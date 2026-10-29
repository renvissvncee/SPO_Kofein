from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

# ---------- Формат ответа с ошибкой ----------


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


# ---------- Исключения приложения ----------


class AppError(Exception):
    status_code: int = 400
    code: str = "BAD_REQUEST"

    def __init__(
        self,
        message: str,
        code: str | None = None,
        details: list[dict[str, Any]] | None = None,
    ):
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        self.details = details


class UnauthorizedError(AppError):
    status_code = 401
    code = "UNAUTHORIZED"


class ForbiddenError(AppError):
    status_code = 403
    code = "FORBIDDEN"


class NotFoundError(AppError):
    status_code = 404
    code = "NOT_FOUND"


class ConflictError(AppError):
    """Нарушено бизнес-правило или уникальность: запрос корректен, но сейчас невыполним."""

    status_code = 409
    code = "CONFLICT"


# Ответы с ошибками для документации OpenAPI
def error_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    descriptions = {
        401: "Нет токена или токен недействителен",
        403: "Нет прав на действие",
        404: "Ресурс не найден",
        409: "Конфликт с текущим состоянием",
        422: "Ошибка валидации запроса",
    }
    return {code: {"model": ErrorResponse, "description": descriptions[code]} for code in codes}


_HTTP_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
}


def _error_json(
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(error=ErrorBody(code=code, message=message, details=details))
    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(body, exclude_none=True),
        headers=headers,
    )


async def _app_error_handler(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, AppError)
    headers = {"WWW-Authenticate": "Bearer"} if error.status_code == 401 else None
    return _error_json(error.status_code, error.code, error.message, error.details, headers)


async def _http_error_handler(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, StarletteHTTPException)
    return _error_json(
        error.status_code,
        _HTTP_CODES.get(error.status_code, "HTTP_ERROR"),
        str(error.detail),
        headers=getattr(error, "headers", None),
    )


async def _validation_error_handler(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, RequestValidationError)
    details = [
        {
            "field": ".".join(str(part) for part in item["loc"]),
            "message": item["msg"],
        }
        for item in error.errors()
    ]
    return _error_json(
        422,
        "VALIDATION_ERROR",
        "Некорректные данные запроса",
        details,
    )


async def _integrity_error_handler(_: Request, error: Exception) -> JSONResponse:
    return _error_json(
        status.HTTP_409_CONFLICT,
        "CONFLICT",
        "Операция нарушает ограничения базы данных",
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_error_handler)
    app.add_exception_handler(IntegrityError, _integrity_error_handler)
