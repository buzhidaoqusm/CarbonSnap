from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["health"])


class Health(BaseModel):
    service: str
    status: str
    message: str


@router.get("/api/health", response_model=Health)
def health_check() -> Health:
    # No envelope: monitors and the compose healthcheck read "status" directly.
    return Health(service="carbonsnap-backend", status="ok", message="Backend is running.")
