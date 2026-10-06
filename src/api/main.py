"""FastAPI 应用入口与 HTTP 路由注册。"""

from fastapi import FastAPI

from api.documents import router as documents_router
from common.logger import logger

# Uvicorn 加载这个应用对象；FastAPI 用它登记和分发 HTTP 请求。
app = FastAPI(title="MODULAR-RAG-SERVICE")
app.include_router(documents_router)
logger.info("FastAPI application initialized")


# 将 GET /health 绑定到下面的函数，返回的字典会自动转换为 JSON。
@app.get("/health", summary="检查服务是否能响应请求")
async def health() -> dict[str, str]:
    """健康检查"""
    return {"status": "ok"}
