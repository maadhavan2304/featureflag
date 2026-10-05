from datetime import date, datetime, timezone
from typing import Annotated, Any, Literal, Optional

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, PlainSerializer


def _to_naive_utc(v: Optional[datetime]) -> Optional[datetime]:
    if v is not None and v.tzinfo is not None:
        v = v.astimezone(timezone.utc).replace(tzinfo=None)
    return v


def _serialize(v: datetime) -> str:
    return v.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")


InDT = Annotated[datetime, AfterValidator(_to_naive_utc)]          # any tz in -> naive UTC
OutDT = Annotated[datetime, PlainSerializer(_serialize, return_type=str, when_used="json")]  # UTC "Z" out


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------- auth / users ----------
class RoleOut(ORM):
    id: int
    name: str
    description: str
    permissions: list[str]


class UserOut(ORM):
    id: int
    email: str
    username: str
    is_active: bool
    role: RoleOut
    created_at: OutDT


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=72)
    role_id: int
    is_active: bool = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=8, max_length=72)
    role_id: Optional[int] = None
    is_active: Optional[bool] = None


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshIn(BaseModel):
    refresh_token: str


# ---------- environments ----------
class EnvironmentOut(BaseModel):
    id: int
    name: str
    key: str
    description: str
    is_production: bool
    sdk_key: Optional[str] = None  # only visible to users with environments:manage
    created_at: OutDT


class EnvironmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    key: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=50)
    description: str = ""
    is_production: bool = False


class EnvironmentUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    description: Optional[str] = None
    is_production: Optional[bool] = None


# ---------- flags / rollouts ----------
class RolloutOut(BaseModel):
    id: int
    flag_id: int
    environment_id: int
    environment_key: str
    environment_name: str
    is_production: bool
    enabled: bool
    rollout_percentage: int
    scheduled_enable_at: Optional[OutDT] = None
    scheduled_disable_at: Optional[OutDT] = None
    version: int
    updated_at: OutDT


class FlagOut(BaseModel):
    id: int
    key: str
    name: str
    description: str
    is_archived: bool
    created_by: Optional[str] = None
    created_at: OutDT
    updated_at: OutDT
    rollouts: list[RolloutOut]


class FlagCreate(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9][a-z0-9_.-]*$", min_length=2, max_length=100)
    name: str = Field(min_length=2, max_length=150)
    description: str = ""


class FlagUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=150)
    description: Optional[str] = None
    is_archived: Optional[bool] = None


class RolloutUpdate(BaseModel):
    """Only fields present in the request body are changed. Send null to clear a schedule."""
    enabled: Optional[bool] = None
    rollout_percentage: Optional[int] = Field(default=None, ge=0, le=100)
    scheduled_enable_at: Optional[InDT] = None
    scheduled_disable_at: Optional[InDT] = None


class RollbackIn(BaseModel):
    audit_log_id: Optional[int] = Field(
        default=None, description="Undo this specific change. Omit to undo the most recent change."
    )


# ---------- assignments ----------
class AssignmentCreate(BaseModel):
    environment_id: int
    user_identifier: str = Field(min_length=1, max_length=255)
    access: Literal["allow", "deny"] = "allow"


class AssignmentOut(ORM):
    id: int
    flag_id: int
    environment_id: int
    user_identifier: str
    access: str
    created_at: OutDT


# ---------- audit ----------
class AuditOut(ORM):
    id: int
    user_id: Optional[int]
    username: str
    action: str
    entity_type: str
    entity_id: Optional[int]
    flag_id: Optional[int]
    flag_key: Optional[str]
    environment_id: Optional[int]
    environment_key: Optional[str]
    before: Optional[Any]
    after: Optional[Any]
    created_at: OutDT


class AuditPage(BaseModel):
    items: list[AuditOut]
    total: int


# ---------- evaluation ----------
class EvaluateIn(BaseModel):
    flag_key: str
    user_id: Optional[str] = None


class EvaluateOut(BaseModel):
    flag_key: str
    enabled: bool
    reason: str


class UsagePoint(BaseModel):
    date: date
    evaluations: int
    enabled_count: int
