from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import time

from common.logger_handler import app_logger


# 限流器
limiter = Limiter(key_func=get_remote_address)

class ProcessTimeMiddleware(BaseHTTPMiddleware):
    """请求处理时间中间件"""
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response

class LoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 记录请求信息
        app_logger.info(f"Request: {request.method} {request.url}")
        
        response = await call_next(request)
        
        # 记录响应信息
        process_time = time.time() - start_time
        app_logger.info(f"Response: {response.status_code} - {process_time:.4f}s")
        
        return response