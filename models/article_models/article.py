from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ArticleBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="文章标题")
    content: str = Field(..., min_length=1, description="文章内容")
    summary: Optional[str] = Field(None, max_length=500, description="文章摘要")
    tags: Optional[List[str]] = Field([], description="标签")
    is_published: bool = Field(False, description="是否发布")

class ArticleCreate(ArticleBase):
    pass

class ArticleUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    summary: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = []
    is_published: Optional[bool] = None

class ArticleResponse(ArticleBase):
    id: int
    author_id: int
    author_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    view_count: int = 0
    
    class Config:
        from_attributes = True