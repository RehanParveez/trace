from fastapi import Request
from fastapi.responses import JSONResponse

class TraceException(Exception):
  def __init__(self, message: str, status_code: int = 400, code: str = "TRACE_ERROR"):
    self.message = message
    self.status_code = status_code
    self.code = code
    super().__init__(message)

async def trace_exception_handler(request: Request, exc: TraceException) -> JSONResponse:
  return JSONResponse(
    status_code=exc.status_code,
    content={"error": {"code": exc.code, "message": exc.message}},
  )