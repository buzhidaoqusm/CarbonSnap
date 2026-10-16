from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: str
    avatar_url: str | None
    bio: str | None
    total_carbon_amount: float
    current_points: int
    created_at: datetime

    @field_serializer("created_at")
    def _naive_iso(self, value: datetime) -> str:
        # Exactly what the Flask route wrote: datetime.isoformat(), no zone.
        return value.isoformat()


class UserResult(BaseModel):
    user: UserOut


class AuthResult(BaseModel):
    user: UserOut
    access_token: str


class AvatarResult(BaseModel):
    avatar_url: str | None


# Request bodies. Fields default to "" and are checked in the route, so a
# missing field gets the same message as before rather than Pydantic's.


class RegisterIn(BaseModel):
    username: str = ""
    email: str = ""
    password: str = ""


class LoginIn(BaseModel):
    email: str = ""
    password: str = ""


class ProfileIn(BaseModel):
    # Absent or null leaves the bio unchanged; "" clears it.
    bio: str | None = None


class AvatarIn(BaseModel):
    image: str = ""
