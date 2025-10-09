import asyncio
import logging

# Set Windows event loop policy at the very beginning to prevent Playwright subprocess issues
import platform
if platform.system() == "Windows":
    try:
        # Use WindowsSelectorEventLoopPolicy for subprocess compatibility
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to set Windows event loop policy: {e}")
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from app.api import router as api_router
from app.api import health
from app.core.config import get_settings
from app.core.logging import setup_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize logging
    setup_logger()
    # Startup tasks (future: warm-ups, health checks, etc.)
    yield
    # Shutdown tasks (future: cleanup, metrics flush, etc.)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    # Basic CORS for local dev; adjust as needed
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", include_in_schema=False)
    async def redirect_to_docs() -> RedirectResponse:
        return RedirectResponse(url="/docs", status_code=307)

    app.include_router(api_router)
    app.include_router(health.router)

    @app.middleware("http")
    async def enforce_cors_and_content_type(request: Request, call_next):
        # Enforce 422 for wrong content type on POST /crawl
        if request.method == "POST" and request.url.path == "/crawl":
            content_type = request.headers.get("content-type", "")
            if not content_type.lower().startswith("application/json"):
                # Raise a RequestValidationError to align with FastAPI's 422 handling
                raise RequestValidationError([{
                    "loc": ["header", "Content-Type"],
                    "msg": "Content-Type must be application/json",
                    "type": "value_error.content_type"
                }])

        response = await call_next(request)

        # Ensure CORS header on GET /health even without Origin
        if request.method == "GET" and request.url.path == "/health":
            if "access-control-allow-origin" not in response.headers:
                response.headers["Access-Control-Allow-Origin"] = "*"

        return response
    @app.exception_handler(RequestValidationError)
    async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
        raw_details = exc.errors()
        details = []
        for err in raw_details:
            err = dict(err)
            # Ensure ctx is JSON serializable
            if "ctx" in err:
                ctx = err["ctx"]
                if isinstance(ctx, dict):
                    err["ctx"] = {k: (str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v)
                                  for k, v in ctx.items()}
                else:
                    err["ctx"] = str(ctx)
            details.append(err)
        return JSONResponse(status_code=422, content={"detail": details})
    return app


app = create_app()
