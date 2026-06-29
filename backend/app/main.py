from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import JSONResponse
from .config import get_settings
from .routers import analytics, auth, executions, schedules, system, users, workflows, workers


settings = get_settings()
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.rate_limit])
app = FastAPI(title="FlowForge API", version="1.0.0", description="AI-powered workflow orchestration and execution platform.")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})


@app.middleware("http")
async def secure_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


app.include_router(system.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(workflows.router)
app.include_router(executions.router)
app.include_router(schedules.router)
app.include_router(workers.router)
app.include_router(analytics.router)
