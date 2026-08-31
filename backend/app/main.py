from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import dispose_engine
from app.core.exceptions import TraceException, trace_exception_handler
from app.core.logging import configure_logging
from app.modules.identity.router import router as identity_router
from app.modules.organizations.router import router as organizations_router
from app.modules.subscriptions.router import router as subscriptions_router
from app.modules.projects.router import router as projects_router
from app.modules.drawings_boq.router import router as drawings_boq_router
from app.modules.whatsapp.router import router as  whatsapp_router
from app.modules.verification.router import router as verification_router

@asynccontextmanager
async def lifespan(app: FastAPI):
  configure_logging()
  yield
  await dispose_engine()

app = FastAPI(
  title=settings.app_name,
  version="0.1.0",
  description="Trace, Construction Intelligence Platform",
  lifespan=lifespan,
)

app.add_exception_handler(TraceException, trace_exception_handler)

app.add_middleware(
  CORSMiddleware,
  allow_origins=settings.cors_origin_list,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(identity_router, prefix=settings.api_v1_prefix)

app.include_router(organizations_router, prefix=settings.api_v1_prefix)

app.include_router(subscriptions_router, prefix=settings.api_v1_prefix)

app.include_router(projects_router, prefix=settings.api_v1_prefix)

app.include_router(drawings_boq_router, prefix=settings.api_v1_prefix)

app.include_router(whatsapp_router, prefix=settings.api_v1_prefix)

app.include_router(verification_router, prefix=settings.api_v1_prefix)

@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
  return {
    "status": "healthy",
    "service": settings.app_name,
    "version": "0.1.0",
  }

@app.get("/ready", tags=["system"])
async def ready() -> dict[str, str]:
  return {"status": "ready"}

@app.get(settings.api_v1_prefix + "/system/ping", tags=["system"])
async def api_ping() -> dict[str, str]:
  return {"message": "Trace API is running"}