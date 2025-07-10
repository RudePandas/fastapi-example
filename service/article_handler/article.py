from fastapi import HTTPException, status
from typing import Optional, Dict, Any
from datetime import datetime
import json

from models.article_models.article import *
from db.async_mysql import async_db

class ArticleService:
    @staticmethod
    async def create_article(article_data: ArticleCreate, author_id: int) -> dict:
        """创建文章"""
        article_id = await async_db.insert('articles', {'title': article_data.title, 
                                        'content': article_data.content,
                                        'summary': article_data.summary,
                                        'tags': json.dumps(article_data.tags),
                                        'is_published': article_data.is_published,
                                        'author_id': author_id,
                                        'created_at': datetime.now()})
        
        return await ArticleService.get_article_by_id(article_id)
    
    @staticmethod
    async def get_articles(page: int = 1, page_size: int = 10, search: Optional[str] = None) -> Dict[str, Any]:
        """获取文章列表"""
        
        # 构建查询条件
        where_clause = "WHERE 1=1"
        params = []
        
        if search:
            where_clause += " AND (a.title LIKE %s OR a.content LIKE %s)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param])
        
        # 获取文章列表
        articles_query = f"""
        SELECT a.*, u.username as author_name
        FROM articles a
        LEFT JOIN users u ON a.author_id = u.id
        {where_clause}
        ORDER BY a.created_at DESC
        """
        articles = await async_db.fetch_paginated(articles_query, page=page, page_size=page_size, params=tuple(params))
        
        # 处理tags字段
        for article in articles['items']:
            if article.get("tags"):
                article["tags"] = json.loads(article["tags"])
        
        return articles
        
    @staticmethod
    async def get_article_by_id(article_id: int) -> Optional[dict]:
        """根据ID获取文章"""
        article = await async_db.fetch_one(
            """
            SELECT a.*, u.username as author_name
            FROM articles a
            LEFT JOIN users u ON a.author_id = u.id
            WHERE a.id = %s
            """,
            (article_id,)
        )
        
        if article and article.get("tags"):
            article["tags"] = json.loads(article["tags"])
        
        return article
    
    @staticmethod
    async def update_article(article_id: int, article_data: ArticleUpdate, user_id: int) -> Optional[dict]:
        """更新文章"""
        # 检查文章是否存在且用户有权限
        article = await async_db.fetch_one(
            "SELECT * FROM articles WHERE id = %s",
            (article_id,)
        )
        
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文章不存在"
            )
        
        # 检查权限（作者或管理员可以编辑）
        user = await async_db.fetch_one(
            "SELECT role FROM users WHERE id = %s",
            (user_id,)
        )
        
        if article["author_id"] != user_id and user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限编辑此文章"
            )
        
        # 构建更新字段
        update_fields = {}
        params = []
        
        if article_data.title is not None:
            update_fields["title"] = article_data.title
        
        if article_data.content is not None:
            update_fields["content"] = article_data.content
        
        if article_data.summary is not None:
            update_fields["summary"] = article_data.summary
        
        if article_data.tags is not None:
            update_fields["tags"] = json.dumps(article_data.tags)
        
        if article_data.is_published is not None:
            update_fields["is_published"] = article_data.is_published
        
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有提供更新字段"
            )
        
        update_fields["updated_at"] = datetime.now()
        where = "id = %s"
        where_params = [article_id]
        
        # 执行更新
        await async_db.update(
            "articles",
            update_fields,
            where,
            where_params
        )
        
        return await ArticleService.get_article_by_id(article_id)
    
    @staticmethod
    async def delete_article(article_id: int, user_id: int) -> bool:
        """删除文章"""
        # 检查文章是否存在且用户有权限
        article = await async_db.fetch_one(
            "SELECT author_id FROM articles WHERE id = %s",
            (article_id,)
        )
        
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文章不存在"
            )
        
        # 检查权限
        user = await async_db.fetch_one(
            "SELECT role FROM users WHERE id = %s",
            (user_id,)
        )
        
        if article["author_id"] != user_id and user["role"] != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限删除此文章"
            )
        
        rows_affected = await async_db.delete(
            "articles",
            "id = %s",
            [article_id]
        )
        return rows_affected > 0