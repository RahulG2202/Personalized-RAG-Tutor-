from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.core.config import redis_settings

redis_client = Redis.from_url(
    redis_settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    socket_connect_timeout=redis_settings.REDIS_SOCKET_CONNECT_TIMEOUT,
    socket_timeout=redis_settings.REDIS_SOCKET_TIMEOUT,
    health_check_interval=redis_settings.REDIS_HEALTH_CHECK_INTERVAL
)

async def ping_redis() -> bool:
    try:
        return bool(await redis_client.ping())
    except RedisError as err:
        print(f"Redis health check failed: {err}")
        return False

async def close_redis() -> None:
    await redis_client.aclose()