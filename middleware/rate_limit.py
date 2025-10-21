from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse

limiter = Limiter(key_func=get_remote_address)

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """Custom rate limit exceeded handler"""
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "detail": str(exc.detail)
        }
    )

# Rate limit configurations
class RateLimitConfig:
    # API endpoints
    CLASSIFY = "10/minute"
    SCHEDULE = "5/minute"
    REVIEW_GENERATE = "3/hour"

    # CRUD operations
    CREATE_ITEM = "30/minute"
    UPDATE_ITEM = "60/minute"
    DELETE_ITEM = "20/minute"

    # Search
    SEARCH = "100/minute"

    # Auth
    LOGIN = "5/minute"
    SIGNUP = "3/hour"

    # Sync
    MCP_SYNC = "10/minute"
