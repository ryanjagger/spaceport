from fastapi import APIRouter

from app import rules
from app.clock import NowDep
from app.schemas import ServerTimeOut

router = APIRouter()


@router.get("/time", response_model=ServerTimeOut)
def server_time(now: NowDep):
    """The server's clock, so the UI never has to trust the device's."""
    return ServerTimeOut(server_now=now, timezone=rules.TZ.key)
