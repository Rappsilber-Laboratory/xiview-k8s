from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import httpx
import logging
import os
import hashlib
import redis.asyncio as redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Configuration from environment variables
REDIS_HOST = os.getenv("REDIS_HOST", "redis-service")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
CACHE_SIZE = os.getenv("CACHE_SIZE", "1gb") 
TARGET_URL = os.getenv("TARGET_URL", "http://crosslinking-api-service:8080")
CACHE_TTL = int(os.getenv("CACHE_TTL", "0"))  # 0 means infinite completely relying on LRU

# Initialize Redis client
redis_client = redis.Redis(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    password=REDIS_PASSWORD or None,
    decode_responses=False
)

@app.on_event("startup")
async def startup_event():
    try:
        # Enforce the cache size limit and eviction policy on Redis automatically
        await redis_client.config_set("maxmemory", CACHE_SIZE)
        await redis_client.config_set("maxmemory-policy", "allkeys-lru")
        logger.info(f"Set Redis cache size limit to {CACHE_SIZE} and policy to allkeys-lru")
    except Exception as e:
        logger.warning(f"Failed to set maxmemory on Redis. Usually requires admin privileges: {e}")

@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy_request(request: Request, full_path: str):
    method = request.method
    url = f"{TARGET_URL}/{full_path}"
    query = request.url.query
    if query:
        url += f"?{query}"
    
    body = await request.body()
    
    # We want to cache specific paths: all network components and annotations
    should_cache = ("get_xiview_" in full_path or "get_annotated_peaklist" in full_path) and method in ["GET", "POST"]
    
    cache_key = None
    if should_cache:
        # Construct cache key uniquely identifying the request
        body_hash = hashlib.md5(body).hexdigest() if body else "empty"
        cache_key = f"xiview_proxy:{full_path}:{query}:{body_hash}"
        
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.info(f"Cache HIT for {full_path}")
                return Response(content=cached_data, media_type="application/json")
        except Exception as e:
            logger.warning(f"Redis get error: {e}")

    # Forward the request if not cached or not cacheable
    logger.info(f"Proxying {method} {url}")
    
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("content-length", None)
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        req = client.build_request(method, url, headers=headers, content=body)
        try:
            proxy_res = await client.send(req)
        except Exception as e:
            logger.error(f"Error communicating with target service: {e}")
            return Response(content=b'{"error": "Bad Gateway"}', status_code=502)
        
        res_body = await proxy_res.aread()

    # Cache successful responses for cacheable paths
    if should_cache and proxy_res.status_code == 200:
        try:
            if CACHE_TTL > 0:
                await redis_client.setex(cache_key, CACHE_TTL, res_body)
                logger.info(f"Cache SET for {full_path} (TTL: {CACHE_TTL}s)")
            else:
                await redis_client.set(cache_key, res_body)
                logger.info(f"Cache SET for {full_path} (Infinite until LRU)")
        except Exception as e:
            logger.warning(f"Redis set error: {e}")

    # Prepare response headers
    res_headers = {}
    for k, v in proxy_res.headers.items():
        if k.lower() not in ["content-encoding", "content-length", "transfer-encoding", "connection"]:
            res_headers[k] = v

    return Response(
        content=res_body,
        status_code=proxy_res.status_code,
        headers=res_headers
    )
