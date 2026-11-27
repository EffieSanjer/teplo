import json
import logging
import time
import uuid
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.config import get_settings
from src.infrastructure.database import get_engine
from src.integrations.product_metadata.routes import router as metadata_router
from src.modules.auth.routes import router as auth_router
from src.modules.feedback.routes import router as feedback_router
from src.modules.gifts.routes import router as gifts_router
from src.modules.media.routes import router as media_router
from src.modules.users.routes import router as users_router
from src.modules.users.invitations import router as friends_router

settings = get_settings()
app = FastAPI(
    title="Friends Wishlist API",
    version="0.1.0",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1/docs",
    redoc_url=None,
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=[urlsplit(settings.origin).hostname])
logger = logging.getLogger("wishlist.requests")
logging.basicConfig(level=logging.INFO, format="%(message)s")


@app.middleware("http")
async def security(request: Request, call_next):
    request_id = str(uuid.uuid4())
    start = time.monotonic()
    origin = request.headers.get("origin")
    if origin and origin != settings.origin:
        response = JSONResponse({"detail": "Недопустимый источник запроса"}, status_code=403)
    elif request.method not in {"GET", "HEAD", "OPTIONS"} and origin != settings.origin:
        response = JSONResponse({"detail": "Требуется Origin"}, status_code=403)
    elif (
        request.headers.get("sec-fetch-site") == "cross-site"
        and origin != settings.origin
        and not (
            request.method in {"GET", "HEAD"}
            and request.headers.get("x-wishlist-request") == "same-origin"
        )
    ):
        # Embedded WebViews can report the outer context as cross-site. Exact
        # Origin takes precedence. Origin-less reads require our custom header:
        # foreign browser pages cannot send it without a CORS preflight, which
        # is denied here. Never exempt writes from the mandatory Origin check.
        response = JSONResponse({"detail": "Межсайтовый запрос запрещён"}, status_code=403)
    else:
        response = await call_next(request)
    # Keep route-specific Cache-Control (e.g. media variants) instead of forcing no-store.
    if "cache-control" not in response.headers:
        response.headers["Cache-Control"] = "private, no-store"
    response.headers.update(
        {
            "X-Request-ID": request_id,
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        }
    )
    # Deliberately omit paths, query strings, body, cookies, identity and exception content.
    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "method": request.method,
                "status": response.status_code,
                "duration_ms": round((time.monotonic() - start) * 1000),
            }
        )
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    # FastAPI's default includes input values (potentially initData and private content).
    errors = [
        {"loc": list(error["loc"]), "msg": error["msg"], "type": error["type"]} for error in exc.errors()
    ]
    return JSONResponse({"detail": errors}, status_code=422)


@app.get("/api/v1/health", tags=["health"])
def health() -> dict[str, str]:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception:
        return JSONResponse({"status": "unavailable"}, status_code=503)


for router in (
    auth_router,
    users_router,
    friends_router,
    gifts_router,
    media_router,
    metadata_router,
    feedback_router,
):
    app.include_router(router, prefix="/api/v1")
