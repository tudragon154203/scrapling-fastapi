# Sprint 13 — API Rate Limit (Specs & Integration Plan)

This sprint introduces consistent rate limiting across the API using Redis-backed counters and FastAPI dependencies. The implementation relies on the fastapi-limiter library, which provides per-route limits via a simple dependency and a single Redis Lua script.

## Summary

- Library: `fastapi-limiter` (Redis required)
- Scope: Apply explicit rate limits to `GET /health` and all `/crawl/*` endpoints
- Concurrency: Gate in-process concurrency for crawl endpoints (per container)
- Operates across replicas: Yes, when all instances share the same Redis

## Policy (authoritative)

- Global for all `/crawl/*`: 15 requests per minute
- `/health`: 60 requests per minute
- Per source/client spam protection: 4 requests per minute per `(IP, base_url)` for `/crawl/*`
- Concurrency for `/crawl/*`: max 4 concurrent requests per container (per running Uvicorn worker)

Notes:
- Rate counts reset on a fixed window basis (not sliding) per fastapi-limiter.
- Concurrency limiting is separate from rate limiting and is enforced per-process.

## Requirements

- Redis server accessible to the API (e.g., `redis://redis:6379/0`)
- Python dependencies:
  - `fastapi-limiter`
  - `redis` (async client used by `fastapi-limiter`)

## Redis & Env Configuration

Add the following environment variables to `.env` (and provision in deployment):

- `RATE_LIMIT_REDIS_URL` (e.g., `redis://localhost:6379/0`)
- `RATE_LIMIT_PREFIX` (default `fastapi-limiter`)

Optional (documented policy; can be hardcoded in code):
- `RATE_LIMIT_CRAWL_RPM=15`
- `RATE_LIMIT_HEALTH_RPM=60`
- `RATE_LIMIT_PER_IP_BASEURL_RPM=4`
- `CRAWL_CONCURRENCY_PER_CONTAINER=4`

Graceful disable behavior (required):
- If `RATE_LIMIT_REDIS_URL` is missing, empty, or invalid, the service must start with rate limiting disabled (no limiter init; no RateLimiter dependencies attached). Log a single startup warning.
- If Redis is unreachable during startup (connection error or script load failure), the service must start with rate limiting disabled and log a warning. It must not block application startup.

## Initialization (official pattern)

Initialize the limiter during app startup and close the Redis connection on shutdown. If configuration is missing or initialization fails, skip limiter wiring entirely and continue without rate limiting. This follows the official fastapi-limiter README with an added fail-open mode.

Pseudo-code for `app/main.py` lifespan:

```py
import redis.asyncio as redis
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_limiter import FastAPILimiter

@asynccontextmanager
async def lifespan(app: FastAPI):
    rl_enabled = False
    rl_url = os.getenv("RATE_LIMIT_REDIS_URL")
    if rl_url:
        try:
            redis_connection = redis.from_url(
                rl_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await FastAPILimiter.init(
                redis_connection,
                prefix=os.getenv("RATE_LIMIT_PREFIX", "fastapi-limiter"),
            )
            rl_enabled = True
        except Exception as exc:
            # Log warning and continue without rate limiting
            app.logger and app.logger.warning(f"Rate limiting disabled: {exc}")
            rl_enabled = False
    else:
        app.logger and app.logger.warning("Rate limiting disabled: RATE_LIMIT_REDIS_URL not set")

    yield
    if rl_enabled:
        await FastAPILimiter.close()
```

Key facts (from official docs):
- `FastAPILimiter.init(redis, prefix=..., identifier=..., http_callback=...)` wires the limiter globally.
- Default identifier uses `X-Forwarded-For` or client IP, plus the request path.
- When the limit is exceeded, it raises HTTP 429 and sets a `Retry-After` header with remaining seconds.

## Mapping policy to routes

fastapi-limiter exposes a `RateLimiter` dependency for HTTP and a `WebSocketRateLimiter` for websockets. We only need HTTP here.

Approach: attach dependencies at the router and route levels, but only when rate limiting is enabled at startup.

1) Global limit for all `/crawl/*` routes (15 rpm)

Attach a router-level dependency so it applies to every crawl endpoint.

```py
from fastapi import APIRouter, Depends
from fastapi_limiter.depends import RateLimiter

router = APIRouter()
if app.state.rate_limit_enabled:  # set during startup
    router.dependencies = [Depends(RateLimiter(times=15, minutes=1))]
```

2) `/health` (60 rpm)

Add a per-route dependency.

```py
deps = []
if app.state.rate_limit_enabled:
    deps.append(Depends(RateLimiter(times=60, minutes=1)))

@router.get("/health", dependencies=deps)
def health():
    return {"status": "ok"}
```

3) Per `(IP, base_url)` for `/crawl/*` (4 rpm)

We need a custom identifier that incorporates the target base URL. Because fastapi-limiter’s identifier only receives the `Request`, you cannot depend on the function parameter model directly. Use one of these patterns:

- Recommended (client-assisted): Require clients to send `X-Target-Host: <host>` where `<host>` is the netloc of the JSON field `url`. The identifier then uses `(client_ip, X-Target-Host)`.
- Or (server-derived): Add a light middleware/dependency that parses the request body once and stores `request.state.target_host` before the rate limiter runs. The identifier reads from `request.state`.

Then, add a second limiter dependency to the crawl router:

```py
router = APIRouter()
if app.state.rate_limit_enabled:
    router.dependencies = [
        Depends(RateLimiter(times=15, minutes=1)),                 # global crawl limiter
        Depends(RateLimiter(times=4, minutes=1, identifier=...)),  # per (IP, base_url)
    ]
```

Important: The library recommends ordering dependencies from strictest to loosest (lowest `window/times` first) to ensure the first failing dependency triggers the callback. Keep the order stable since dependency order participates in the storage key.

## Concurrency limit (per container)

fastapi-limiter controls request rate over time, not simultaneous concurrency. Enforce concurrency separately at the process level:

- Use an `asyncio.Semaphore(4)` (or `anyio.CapacityLimiter(4)`) held in app state.
- Guard crawl endpoints with a small dependency/context manager: `async with semaphore`.

This keeps at most 4 concurrent crawl requests per running worker, independent of rate limiting. For multi-worker setups, concurrency is per worker process.

## Proxies and client IP

- The default identifier honors the `X-Forwarded-For` header. Ensure your ingress (e.g., NGINX/Traefik/Cloudflare) sets it correctly.
- If your deployment uses a proxy chain, configure Uvicorn/Gunicorn to trust proxy headers or override the identifier.

## Observability & errors

- Exceeding a limit returns `429 Too Many Requests` with `Retry-After: <seconds>`.
- Keys are stored in Redis as: `{prefix}:{rate_key}:{route_index}:{dep_index}`.
- Windowing is fixed (first hit sets TTL; increments until limit; overflow returns remaining TTL in ms).

## Testing & acceptance criteria

Acceptance:
- `POST /crawl` and `/crawl/*` respect a 15 rpm cap across replicas.
- `GET /health` allows 60 rpm.
- Additional 4 rpm cap applies per `(IP, base_url)` on crawl endpoints.
- At most 4 crawl requests execute concurrently per container.

Suggested tests:
- Send >15 requests/min to a crawl route; assert a 429 with `Retry-After`.
- Send >4 requests/min from the same IP to the same target host; assert a 429.
- Fire 10 concurrent crawl requests; measure that only 4 run simultaneously (others wait or are queued, depending on the chosen semaphore strategy).

## Out of scope (this sprint)

- Sliding windows, token bucket, or distributed concurrency across replicas
- Per-user auth-aware quotas (can be added later via a custom identifier)

## References

- fastapi-limiter (README): https://github.com/long2ice/fastapi-limiter
- PyPI: https://pypi.org/project/fastapi-limiter/

## Implementation notes (for maintainers)

- Wire Redis in `app/main.py` lifespan and call `FastAPILimiter.init(...)`.
- Add router-level and per-route dependencies in `app/api/routes.py` as described above.
- Choose and implement the `(IP, base_url)` identifier strategy (header-based is simplest and avoids reading the JSON body in the limiter).
- Add a small concurrency guard (semaphore) for crawl endpoints; keep the value configurable via env.
