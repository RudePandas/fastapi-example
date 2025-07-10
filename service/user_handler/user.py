from fastapi import HTTPException, status
from typing import Optional, Dict, Any
from datetime import datetime

from db.async_mysql import async_db
from common.auth import auth_manager
from models.user_models.user import *

class UserService:
    @staticmethod
    async def authenticate_user(username: str, password: str) -> Optional[dict]:
        """用户认证"""
        user = await async_db.fetch_one(
            "SELECT * FROM users WHERE username = %s AND is_active = 1",
            (username,)
        )
        if not user or not auth_manager.verify_password(password, user["password_hash"]):
            return None
        
        return user
    
    @staticmethod
    async def create_user(user_data: UserCreate) -> dict:
        """创建用户"""
        # 检查用户名是否已存在
        existing_user = await async_db.fetch_one(
            "SELECT id FROM users WHERE username = %s OR email = %s",
            (user_data.username, user_data.email)
        )
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名或邮箱已存在"
            )
        
        # 创建用户
        password_hash = auth_manager.get_password_hash(user_data.password)
        user_id = await async_db.insert('users', {'username': user_data.username, 
                                        'email': user_data.email,
                                        'full_name': user_data.full_name,
                                        'password_hash': password_hash,
                                        'role': user_data.role.value,
                                        'status': user_data.status.value,
                                        'is_active': True,
                                        'created_at': datetime.now()})
        
        # 返回新创建的用户
        return await async_db.fetch_one(
            "SELECT * FROM users WHERE id = %s",
            (user_id,)
        )
    
    @staticmethod
    async def get_users(page: int = 1, page_size: int = 10, search: Optional[str] = None) -> Dict[str, Any]:
        """获取用户列表"""
        
        # 构建查询条件
        where_clause = "WHERE 1=1"
        params = []
        
        if search:
            where_clause += " AND (username LIKE %s OR email LIKE %s OR full_name LIKE %s)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
        
        
        # 获取用户列表
        users_query = f"""
        SELECT id, username, email, full_name, role, status, is_active, created_at, updated_at
        FROM users {where_clause}
        ORDER BY created_at DESC
        """
        
        users = await async_db.fetch_paginated(users_query, page=page, page_size=page_size, params=tuple(params))
        return users
        
    
    @staticmethod
    async def get_user_by_id(user_id: int) -> Optional[dict]:
        """根据ID获取用户"""
        return await async_db.fetch_one(
            "SELECT * FROM users WHERE id = %s",
            (user_id,)
        )
    
    @staticmethod
    async def update_user(user_id: int, user_data: UserUpdate) -> Optional[dict]:
        """更新用户"""
        # 构建更新字段
        update_fields = {}
        params = []
        
        if user_data.username is not None:
            update_fields["username"] = user_data.username
        
        if user_data.email is not None:
            update_fields["email"] = user_data.email
        
        if user_data.full_name is not None:
            update_fields["full_name"] = user_data.full_name
        
        if user_data.role is not None:
            update_fields["role"] = user_data.role.value
        
        if user_data.status is not None:
            update_fields["status"] = user_data.status.value
        
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有提供更新字段"
            )
        
        update_fields["updated_at"] = datetime.now()
        where = f"id = %s"
        where_params = [user_id]
        
        # 执行更新
        await async_db.update(
            'users',
            update_fields,
            where,
            where_params
        )
        
        # 返回更新后的用户
        return await UserService.get_user_by_id(user_id)
    
    @staticmethod
    async def delete_user(user_id: int) -> bool:
        """删除用户"""
        rows_affected = await async_db.delete(
            "users",
            "id=%s",
            [user_id]
        )
        return rows_affected > 0