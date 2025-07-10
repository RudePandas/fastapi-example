from fastapi import APIRouter, HTTPException, Depends, Query, status, Request
from typing import Optional
from datetime import datetime
import logging
from fastapi.security import OAuth2PasswordRequestForm

from common.middleware import limiter
from models.user_models.user import *
from models.base import *
from service.user_handler.user import *
from common.auth import *


router_token = APIRouter(prefix="", tags=["token"])

@router_token.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录获取访问令牌"""
    user = await UserService.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth_manager.create_access_token(
        data={"sub": user["username"]}
    )
    return {"access_token": access_token, "token_type": "bearer"}

router_others = APIRouter(prefix="/api/v1/others", tags=["其他"])

# 路由定义
@router_others.get("")
async def root():
    return {"message": "FastAPI RESTful API 服务正在运行"}

@router_others.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

router_auth = APIRouter(prefix="/api/v1/auth", tags=["认证"])

# 认证相关路由
@router_auth.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(request: Request, form_data: UserLogin):
    """用户登录"""
    user = await UserService.authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth_manager.create_access_token(
        data={"sub": user["username"]}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router_auth.post("/register", response_model=StandardResponse)
@limiter.limit("3/minute")
async def register(request: Request, user: UserCreate):
    """用户注册"""
    new_user = await UserService.create_user(user)
    return StandardResponse(
        message="注册成功",
        data={"user_id": new_user["id"], "username": new_user["username"]}
    )

@router_auth.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_active_user)):
    """获取当前用户信息"""
    return current_user

router_users = APIRouter(prefix="/api/v1/users", tags=["用户管理"])

# 用户管理路由
@router_users.get("", response_model=PaginatedResponse)
@limiter.limit("30/minute")
async def get_users(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """获取用户列表（管理员权限）"""
    result = await UserService.get_users(page, page_size, search)
    return result

@router_users.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: dict = Depends(get_current_active_user)
):
    """获取用户详情"""
    # 用户只能查看自己的信息，管理员可以查看所有用户
    if current_user["id"] != user_id and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限查看此用户信息"
        )
    
    user = await UserService.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return user

@router_users.put("/{user_id}", response_model=StandardResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_active_user)
):
    """更新用户信息"""
    # 用户只能更新自己的信息，管理员可以更新所有用户
    if current_user["id"] != user_id and current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权限更新此用户信息"
        )
    
    # 非管理员不能更改角色和状态
    if current_user["role"] != "admin":
        user_update.role = None
        user_update.status = None
    
    updated_user = await UserService.update_user(user_id, user_update)
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return StandardResponse(
        message="用户信息更新成功",
        data={"user_id": updated_user["id"]}
    )

@router_users.delete("/{user_id}", response_model=StandardResponse)
async def delete_user(
    user_id: int,
    current_user: dict = Depends(require_role(UserRole.ADMIN))
):
    """删除用户（管理员权限）"""
    success = await UserService.delete_user(user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    return StandardResponse(message="用户删除成功")
