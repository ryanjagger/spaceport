from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db import SessionDep
from app.errors import error_response

router = APIRouter()


@router.get("/health")
def health(session: SessionDep):
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return error_response(503, "database_unavailable", "The database is not reachable.")
    return {"status": "ok"}
