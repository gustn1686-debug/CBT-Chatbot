from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """API 명세의 에러 포맷 { code, message } 로 응답되는 예외."""

    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"code": exc.code, "message": exc.message}
        )
