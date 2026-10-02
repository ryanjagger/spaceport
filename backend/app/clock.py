from datetime import datetime
from typing import Annotated

from fastapi import Depends

from app import rules


def get_now() -> datetime:
    """The server's clock, read once per request and passed down. Tests override this."""
    return datetime.now(rules.TZ)


NowDep = Annotated[datetime, Depends(get_now)]
