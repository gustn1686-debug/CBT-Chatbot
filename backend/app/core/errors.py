from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
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

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        # 명세 포맷으로 통일. 첫 번째 오류의 메시지를 사람이 읽을 수 있게 내려준다.
        first = exc.errors()[0] if exc.errors() else {}
        message = str(first.get("msg", "요청 값이 올바르지 않습니다.")).removeprefix(
            "Value error, "
        )
        return JSONResponse(
            status_code=422, content={"code": "validation_error", "message": message}
        )
