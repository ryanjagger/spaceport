"""One error envelope for every failure: {"error": {"code": ..., "message": ...}}."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.rules import RuleViolation

log = logging.getLogger("spaceport.errors")

# The request was valid but the world moved on: 409. Anything else a rule rejects: 422.
STATE_DEPENDENT_CODES = {"booking_conflict", "in_the_past", "already_started", "already_cancelled"}


class NotFoundError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code, content={"error": {"code": code, "message": message}}
    )


def _describe(error: dict) -> str:
    # ("body", "startTime") -> "startTime"; ("query", "date") -> "date"
    field = ".".join(str(part) for part in error["loc"][1:])
    return f"{field}: {error['msg']}" if field else error["msg"]


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RuleViolation)
    def rule_violation(request: Request, exc: RuleViolation) -> JSONResponse:
        status_code = 409 if exc.code in STATE_DEPENDENT_CODES else 422
        return error_response(status_code, exc.code, exc.message)

    @app.exception_handler(NotFoundError)
    def not_found(request: Request, exc: NotFoundError) -> JSONResponse:
        return error_response(404, "not_found", exc.message)

    @app.exception_handler(RequestValidationError)
    def invalid_request(request: Request, exc: RequestValidationError) -> JSONResponse:
        message = "; ".join(_describe(error) for error in exc.errors())
        return error_response(422, "validation_error", message)

    @app.exception_handler(HTTPException)
    def http_error(request: Request, exc: HTTPException) -> JSONResponse:
        if exc.status_code == 404:
            code = "not_found"
        elif exc.status_code < 500:
            code = "validation_error"
        else:
            code = "internal_error"
        return error_response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    def unhandled(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error on %s %s", request.method, request.url.path)
        return error_response(500, "internal_error", "Something went wrong on our side.")
