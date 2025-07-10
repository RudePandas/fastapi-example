from fastapi import APIRouter, HTTPException, Depends, Query, status, Request
from typing import Optional
import logging
import asyncio

from db.async_mysql import async_db
from common.middleware import limiter
from models.article_models.article import *
from service.article_handler.article import *
from common.auth import *

router_articles = APIRouter(prefix="/api/v1/articles", tags=["文章管理"])

@router_articles.get("", response_model=PaginatedResponse)
@limiter.limit("60/minute")
async def get_articles(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词")
):
    """获取文章列表"""
    result = await ArticleService.get_articles(page, page_size, search)
    return result

@router_articles.get("/{article_id}", response_model=ArticleResponse)
@limiter.limit("100/minute")
async def get_article(request: Request, article_id: int):
    """获取文章详情"""
    article = await ArticleService.get_article_by_id(article_id)
    if not article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在"
        )
    
    # 增加浏览量
    update_fields = {"view_count": article["view_count"] + 1}
    where = "id = %s"
    where_params = [article_id]
    await async_db.update(
        "articles",
        update_fields,
        where,
        where_params
    )
    
    return article

@router_articles.post("", response_model=StandardResponse)
@limiter.limit("10/minute")
async def create_article(
    request: Request,
    article: ArticleCreate,
    current_user: dict = Depends(get_current_active_user)
):
    """创建文章"""
    new_article = await ArticleService.create_article(article, current_user["id"])
    return StandardResponse(
        message="文章创建成功",
        data={"article_id": new_article["id"]}
    )

@router_articles.put("/{article_id}", response_model=StandardResponse)
async def update_article(
    article_id: int,
    article_update: ArticleUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """更新文章"""
    updated_article = await ArticleService.update_article(
        article_id, article_update, current_user["id"]
    )
    if not updated_article:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在"
        )
    
    return StandardResponse(
        message="文章更新成功",
        data={"article_id": updated_article["id"]}
    )

@router_articles.delete("/{article_id}", response_model=StandardResponse)
async def delete_article(
    article_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """删除文章"""
    success = await ArticleService.delete_article(article_id, current_user["id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在"
        )
    
    return StandardResponse(message="文章删除成功")

router_stats = APIRouter(prefix="/api/v1/stats", tags=["统计分析"])

# 统计和分析路由
@router_stats.get("/overview", response_model=StandardResponse)
async def get_stats_overview(
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """获取统计概览（管理员权限）"""
    # 用户统计
    user_stats = await async_db.fetch_all("""
        SELECT 
            COUNT(*) as total_users,
            COUNT(CASE WHEN status = 'active' THEN 1 END) as active_users,
            COUNT(CASE WHEN role = 'admin' THEN 1 END) as admin_users,
            COUNT(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 END) as new_users_week
        FROM users
    """)
    
    # 文章统计
    article_stats = await async_db.fetch_all("""
        SELECT 
            COUNT(*) as total_articles,
            COUNT(CASE WHEN is_published = 1 THEN 1 END) as published_articles,
            SUM(view_count) as total_views,
            COUNT(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 END) as new_articles_week
        FROM articles
    """)
    
    return StandardResponse(
        message="统计数据获取成功",
        data={
            "user_stats": user_stats[0] if user_stats else {},
            "article_stats": article_stats[0] if article_stats else {}
        }
    )

@router_stats.get("/popular")
async def get_popular_articles(
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
    current_user: dict = Depends(get_current_active_user)
):
    """获取热门文章"""
    articles = await async_db.fetch_all("""
        SELECT a.id, a.title, a.view_count, a.created_at, u.username as author_name
        FROM articles a
        LEFT JOIN users u ON a.author_id = u.id
        WHERE a.is_published = 1
        ORDER BY a.view_count DESC
        LIMIT %s
    """, (limit,))
    
    return StandardResponse(
        message="热门文章获取成功",
        data=articles
    )

# 高级搜索API
@router_stats.get("/search")
@limiter.limit("30/minute")
async def advanced_search(
    request: Request,
    q: str = Query(..., description="搜索关键词"),
    type: str = Query("all", regex="^(all|articles|users)$", description="搜索类型"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=50, description="每页数量")
):
    """高级搜索"""
    results = {"articles": [], "users": []}
    
    if type in ["all", "articles"]:
        # 搜索文章
        articles = await async_db.fetch_all("""
            SELECT a.id, a.title, a.summary, a.created_at, u.username as author_name,
                   MATCH(a.title, a.content) AGAINST(%s IN BOOLEAN MODE) as relevance
            FROM articles a
            LEFT JOIN users u ON a.author_id = u.id
            WHERE a.is_published = 1 AND (
                MATCH(a.title, a.content) AGAINST(%s IN BOOLEAN MODE) OR
                a.title LIKE %s OR a.content LIKE %s
            )
            ORDER BY relevance DESC, a.created_at DESC
            LIMIT %s OFFSET %s
        """, (q, q, f"%{q}%", f"%{q}%", page_size, (page - 1) * page_size))
        
        results["articles"] = articles
    
    if type in ["all", "users"]:
        # 搜索用户
        users = await async_db.fetch_all("""
            SELECT id, username, full_name, created_at
            FROM users
            WHERE is_active = 1 AND (
                username LIKE %s OR full_name LIKE %s
            )
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """, (f"%{q}%", f"%{q}%", page_size, (page - 1) * page_size))
        
        results["users"] = users
    
    return StandardResponse(
        message="搜索完成",
        data=results
    )

# 批量操作API
@router_stats.post("/batch")
async def batch_article_operations(
    request: Request,
    operations: List[Dict[str, Any]],
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """批量文章操作（管理员权限）"""
    results = []
    
    for operation in operations:
        try:
            op_type = operation.get("type")
            article_id = operation.get("article_id")
            
            if op_type == "publish":
                await async_db.execute(
                    "UPDATE articles SET is_published = 1 WHERE id = %s",
                    (article_id,)
                )
                results.append({"article_id": article_id, "status": "published"})
            
            elif op_type == "unpublish":
                res = await async_db.execute(
                    "UPDATE articles SET is_published = 0 WHERE id = %s",
                    (article_id,)
                )
                results.append({"article_id": article_id, "status": "unpublished"})
            
            elif op_type == "delete":
                await async_db.execute(
                    "DELETE FROM articles WHERE id = %s",
                    (article_id,)
                )
                results.append({"article_id": article_id, "status": "deleted"})
            
        except Exception as e:
            results.append({
                "article_id": article_id,
                "status": "error",
                "error": str(e)
            })
    
    return StandardResponse(
        message="批量操作完成",
        data=results
    )

# 导出API
@router_stats.get("/export")
async def export_articles(
    format: str = Query("json", regex="^(json|csv)$", description="导出格式"),
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """导出文章数据（管理员权限）"""
    articles = await async_db.fetch_all("""
        SELECT a.id, a.title, a.content, a.summary, a.is_published, 
               a.view_count, a.created_at, u.username as author_name
        FROM articles a
        LEFT JOIN users u ON a.author_id = u.id
        ORDER BY a.created_at DESC
    """)
    
    if format == "json":
        # 将 datetime 字段转为字符串
        for article in articles:
            if isinstance(article.get('created_at'), datetime):
                article['created_at'] = article['created_at'].isoformat()
        from fastapi.responses import JSONResponse
        return JSONResponse(content=articles)
    
    elif format == "csv":
        import csv
        import io
        from fastapi.responses import StreamingResponse
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=articles[0].keys() if articles else [])
        writer.writeheader()
        writer.writerows(articles)
        
        response = StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=articles.csv"}
        )
        return response

# WebSocket示例
# @app.websocket("/ws/notifications")
# async def websocket_notifications(websocket):
#     """WebSocket通知推送"""
#     await websocket.accept()
#     try:
#         while True:
#             # 这里可以实现实时通知逻辑
#             await websocket.send_text("实时通知消息")
#             await asyncio.sleep(30)  # 每30秒发送一次
#     except Exception as e:
#         logger.error(f"WebSocket连接错误: {e}")
#     finally:
#         await websocket.close()
