"""Idempotent seed: roles, environments, admin user and a few demo flags.

    python -m app.seed
"""
from sqlalchemy import select

from .config import settings
from .database import SessionLocal
from .deps import DEFAULT_ROLES
from .models import Environment, FeatureFlag, Role, User
from .routers.environments import new_sdk_key
from .security import hash_password
from .services.rollouts import ensure_rollouts_for_flag


def run() -> None:
    db = SessionLocal()
    try:
        for name, (desc, perms) in DEFAULT_ROLES.items():
            role = db.scalar(select(Role).where(Role.name == name))
            if role:
                role.permissions, role.description = perms, desc
            else:
                db.add(Role(name=name, description=desc, permissions=perms))
        db.flush()

        for key, name, prod in (("development", "Development", False), ("testing", "Testing", False),
                                ("production", "Production", True)):
            if not db.scalar(select(Environment).where(Environment.key == key)):
                db.add(Environment(key=key, name=name, is_production=prod, sdk_key=new_sdk_key(key),
                                   description=f"{name} environment"))
        db.flush()

        admin_role = db.scalar(select(Role).where(Role.name == "admin"))
        admin = db.scalar(select(User).where(User.username == settings.ADMIN_USERNAME))
        if not admin:
            admin = User(email=settings.ADMIN_EMAIL, username=settings.ADMIN_USERNAME,
                         hashed_password=hash_password(settings.ADMIN_PASSWORD), role_id=admin_role.id)
            db.add(admin)
            db.flush()

        demo = [("new-checkout", "New checkout flow", "Redesigned one-page checkout."),
                ("dark-mode", "Dark mode", "Theme switcher in user settings."),
                ("ai-search", "AI search", "Semantic search powered by embeddings.")]
        for key, name, desc in demo:
            if not db.scalar(select(FeatureFlag).where(FeatureFlag.key == key)):
                flag = FeatureFlag(key=key, name=name, description=desc, created_by=admin.id)
                db.add(flag)
                db.flush()
                ensure_rollouts_for_flag(db, flag)
        db.commit()
        print(f"Seed complete. Login: {settings.ADMIN_USERNAME} / {settings.ADMIN_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    run()
