"""Flag evaluation, caching and usage tracking."""
import hashlib
import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..models import FeatureFlag, FeatureRollout, FeatureUsage, UserAssignment, utcnow
from .. import redis_client as rc


# ---------- cache ----------
def cfg_key(env_id: int, flag_key: str) -> str:
    return f"ff:cfg:{env_id}:{flag_key}"


def invalidate(env_id: Optional[int], flag_key: str) -> None:
    """Drop cached config for a flag (one environment, or all if env_id is None)."""
    r = rc.get_redis()
    if env_id is not None:
        rc.cache_delete(cfg_key(env_id, flag_key))
    elif r:
        try:
            keys = list(r.scan_iter(f"ff:cfg:*:{flag_key}"))
            rc.cache_delete(*keys)
        except Exception:
            pass


def load_config(db: Session, env_id: int, flag_key: str) -> Optional[dict]:
    cached = rc.cache_get(cfg_key(env_id, flag_key))
    if cached is not None:
        return cached
    flag = db.scalar(select(FeatureFlag).where(FeatureFlag.key == flag_key))
    if not flag:
        return None
    r = db.scalar(select(FeatureRollout).where(FeatureRollout.flag_id == flag.id,
                                               FeatureRollout.environment_id == env_id))
    if not r:
        return None
    rows = db.scalars(select(UserAssignment).where(UserAssignment.flag_id == flag.id,
                                                    UserAssignment.environment_id == env_id)).all()
    cfg = {
        "flag_id": flag.id, "environment_id": env_id, "archived": flag.is_archived,
        "enabled": r.enabled, "percentage": r.rollout_percentage,
        "allow": [a.user_identifier for a in rows if a.access == "allow"],
        "deny": [a.user_identifier for a in rows if a.access == "deny"],
    }
    rc.cache_set(cfg_key(env_id, flag_key), cfg, settings.CACHE_TTL_SECONDS)
    return cfg


# ---------- evaluation ----------
def bucket(flag_key: str, user_id: str) -> int:
    """Deterministic 0-99 bucket: a user always lands in the same bucket for a flag."""
    digest = hashlib.sha256(f"{flag_key}:{user_id}".encode()).hexdigest()
    return int(digest[:8], 16) % 100


def evaluate_config(flag_key: str, cfg: Optional[dict], user_id: Optional[str]) -> tuple[bool, str]:
    """Order: archived > deny list > allow list > global switch > percentage rollout."""
    if cfg is None:
        return False, "flag_not_found"
    if cfg["archived"]:
        return False, "archived"
    if user_id and user_id in cfg["deny"]:
        return False, "user_denied"
    if user_id and user_id in cfg["allow"]:
        return True, "user_allowed"
    if not cfg["enabled"]:
        return False, "disabled"
    pct = cfg["percentage"]
    if pct >= 100:
        return True, "enabled"
    if pct <= 0:
        return False, "rollout_0_percent"
    if not user_id:
        return False, "user_id_required_for_percentage_rollout"
    return (True, "in_rollout") if bucket(flag_key, user_id) < pct else (False, "outside_rollout")


# ---------- usage tracking ----------
def record_usage(db: Session, flag_id: int, env_id: int, enabled: bool) -> None:
    r = rc.get_redis()
    if r:
        try:
            key = f"ff:usage:{date.today().isoformat()}"
            pipe = r.pipeline()
            pipe.hincrby(key, f"{flag_id}:{env_id}:t", 1)
            if enabled:
                pipe.hincrby(key, f"{flag_id}:{env_id}:e", 1)
            pipe.expire(key, 86400 * 3)
            pipe.execute()
            return
        except Exception:
            rc._mark_down()
    _upsert_usage(db, date.today(), flag_id, env_id, 1, 1 if enabled else 0)
    db.commit()


def _upsert_usage(db: Session, day: date, flag_id: int, env_id: int, total: int, enabled: int) -> None:
    row = db.scalar(select(FeatureUsage).where(FeatureUsage.flag_id == flag_id,
                                               FeatureUsage.environment_id == env_id,
                                               FeatureUsage.usage_date == day))
    if row:
        row.evaluations += total
        row.enabled_count += enabled
    else:
        db.add(FeatureUsage(flag_id=flag_id, environment_id=env_id, usage_date=day,
                            evaluations=total, enabled_count=enabled))


def flush_usage(db: Session) -> None:
    """Moves Redis counters into MySQL. Each key is renamed first so no increments are lost."""
    r = rc.get_redis()
    if not r:
        return
    try:
        for key in list(r.scan_iter("ff:usage:*")):
            day = date.fromisoformat(key.split(":")[-1])
            tmp = f"ff:flush:{day.isoformat()}:{uuid.uuid4().hex}"
            try:
                r.rename(key, tmp)
            except Exception:
                continue  # already flushed by another worker
            counts: dict[tuple[int, int], list[int]] = {}
            for field, value in r.hgetall(tmp).items():
                f_id, e_id, kind = field.split(":")
                c = counts.setdefault((int(f_id), int(e_id)), [0, 0])
                c[0 if kind == "t" else 1] += int(value)
            for (f_id, e_id), (total, enabled) in counts.items():
                _upsert_usage(db, day, f_id, e_id, total, enabled)
            db.commit()
            r.delete(tmp)
    except Exception:
        db.rollback()
