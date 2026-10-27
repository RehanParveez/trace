from __future__ import annotations
import logging
from pathlib import Path
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

log = logging.getLogger("trace.schema")

BACKEND = Path(__file__).resolve().parents[2]
SCHEMA_BEHIND_MESSAGE = (
  "The database is behind the code: a migration has not been applied. "
  "Run `alembic upgrade head` in the backend folder, restart the API and the worker, then try again."
)
_MISSING_SQLSTATES = {"42P01", "42703"}
_MISSING_NAMES = ("UndefinedTableError", "UndefinedColumnError")

def code_heads() -> set[str] | None:
  folder = BACKEND / "alembic"
  if not (folder / "versions").is_dir():
    return None
  try:
    from alembic.config import Config
    from alembic.script import ScriptDirectory
    cfg = Config()

    cfg.set_main_option("script_location", str(folder))
    return set(ScriptDirectory.from_config(cfg).get_heads())
  except Exception: 
    log.exception("could not read the migration scripts")
    return None

async def database_revisions(engine) -> set[str] | None:
  try:
    async with engine.connect() as conn:
      rows = (await conn.execute(text("SELECT version_num FROM alembic_version"))).all()
    return {r[0] for r in rows}
  except DBAPIError as e:
    if is_schema_error(e):
      return None  
    raise

async def check(engine) -> dict:
  heads = code_heads()

  if heads is None:
    return {"state": "UNKNOWN", "reason": "migration scripts not found", "code": [], "database": []}
  try:
    db = await database_revisions(engine)
  except Exception as e:  
    return {"state": "UNKNOWN", "reason": "database not reachable: " + type(e).__name__, "code": sorted(heads), "database": []}
  if db is None:
    return {"state": "BEHIND", "reason": "no migration has been applied", "code": sorted(heads), "database": []}
  if heads - db:
    return {"state": "BEHIND", "reason": "newer migrations exist", "code": sorted(heads), "database": sorted(db)}
  if db - heads:
    return {"state": "AHEAD", "reason": "the database has a revision this code does not know", "code": sorted(heads), "database": sorted(db)}
  return {"state": "OK", "reason": None, "code": sorted(heads), "database": sorted(db)}

def is_schema_error(exc: BaseException) -> bool:
  seen: list[BaseException] = []
  cur: BaseException | None = exc

  while cur is not None and len(seen) < 4:
    seen.append(cur)
    cur = getattr(cur, "orig", None) or cur.__cause__
  for e in seen:
    code = getattr(e, "sqlstate", None) or getattr(e, "pgcode", None)
    if code in _MISSING_SQLSTATES:
      return True
    if type(e).__name__ in _MISSING_NAMES:
      return True
  text_ = " ".join(str(e) for e in seen)
  return any(n in text_ for n in _MISSING_NAMES) or (
    "does not exist" in text_ and ("column" in text_ or "relation" in text_)
  )

async def db_error_handler(request: Request, exc: DBAPIError):
  if is_schema_error(exc):
    log.error("schema behind code on %s: %s", request.url.path, str(getattr(exc, "orig", exc))[:200])
    return JSONResponse(
      status_code=503,
      content={"error": {"code": "SCHEMA_BEHIND", "message": SCHEMA_BEHIND_MESSAGE}},
    )
  raise exc
