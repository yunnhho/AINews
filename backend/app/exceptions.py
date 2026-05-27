from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class AppError(HTTPException):
    def __init__(self, code: str, message: str, status_code: int):
        self.code = code
        super().__init__(status_code=status_code, detail={"code": code, "message": message})


# ── 공통 에러 ─────────────────────────────────────
class NotFoundError(AppError):
    def __init__(self, resource: str = "리소스"):
        super().__init__(
            code=f"{resource.upper()}_NOT_FOUND",
            message=f"요청한 {resource}을(를) 찾을 수 없습니다.",
            status_code=404,
        )


class UnauthorizedError(AppError):
    def __init__(self, message: str = "인증이 필요합니다."):
        super().__init__(code="UNAUTHORIZED", message=message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "접근 권한이 없습니다."):
        super().__init__(code="FORBIDDEN", message=message, status_code=403)


class ConflictError(AppError):
    def __init__(self, code: str, message: str):
        super().__init__(code=code, message=message, status_code=409)


# ── 핸들러 ────────────────────────────────────────
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.detail["message"], "status": exc.status_code}},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(exc.detail), "status": exc.status_code}},
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "INTERNAL_SERVER_ERROR", "message": "서버 오류가 발생했습니다.", "status": 500}},
    )
