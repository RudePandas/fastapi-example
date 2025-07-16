from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import uvicorn
import logging

from conf import my_config
from common.middleware import ProcessTimeMiddleware, LoggingMiddleware, limiter, RateLimitExceeded, _rate_limit_exceeded_handler
from common.auth import *
from api.user_api.user import router_auth, router_users, \
                            router_others, router_token
from api.article_handler.article import router_articles, router_stats
from common.logger_handler import app_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    # await db_manager.create_pool()
    # await create_tables()
    app_logger.info("应用启动完成")
    
    yield
    
    # 关闭时执行
    # await db_manager.close_pool()
    app_logger.info("应用关闭完成")

# 创建FastAPI应用
app = FastAPI(
    title=my_config.settings.project_name,
    description="FastAPI RESTful API 高级实现",
    version="1.0.0",
    lifespan=lifespan
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ProcessTimeMiddleware)
app.add_middleware(LoggingMiddleware)

# 添加限流处理
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(router_auth)
app.include_router(router_token)
app.include_router(router_users)
app.include_router(router_others)
app.include_router(router_articles)
app.include_router(router_stats)


# 异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "message": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    app_logger.error(f"未处理的异常: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "服务器内部错误"}
    )
    

# 启动应用
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )