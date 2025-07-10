import asyncio
import aiomysql
from typing import Any, Dict, List, Optional, Union, Tuple
from contextlib import asynccontextmanager
import logging
from concurrent.futures import ThreadPoolExecutor
import threading
import atexit
import weakref

class AsyncMySQLHandler:
    """
    异步MySQL操作类 - 单实例模式
    支持连接池、事务、线程池执行
    自动初始化和清理连接池
    """
    
    _instance = None
    _lock = threading.Lock()
    _cleanup_registered = False
    
    def __new__(cls, *args, **kwargs):
        """单实例模式实现"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    # 注册程序退出时的清理函数
                    if not cls._cleanup_registered:
                        atexit.register(cls._cleanup_on_exit)
                        cls._cleanup_registered = True
        return cls._instance
    
    @classmethod
    def _cleanup_on_exit(cls):
        """程序退出时的清理函数"""
        if cls._instance and cls._instance.pool:
            try:
                # 在同步环境中强制关闭连接池
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(cls._instance._force_close())
                loop.close()
            except Exception as e:
                logging.getLogger(__name__).error(f"程序退出时清理连接池失败: {e}")
    
    async def _force_close(self):
        """强制关闭连接池（内部使用）"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=False)
    
    def __init__(self, 
                 host: str = 'localhost',
                 port: int = 3306,
                 user: str = 'root',
                 password: str = '123456',
                 database: str = 'fastapi_db',
                 charset: str = 'utf8mb4',
                 pool_size: int = 10,
                 max_pool_size: int = 20,
                 thread_pool_size: int = 5):
        """
        初始化数据库连接配置
        
        Args:
            host: 数据库主机
            port: 端口号
            user: 用户名
            password: 密码
            database: 数据库名
            charset: 字符集
            pool_size: 连接池初始大小
            max_pool_size: 连接池最大大小
            thread_pool_size: 线程池大小
        """
        # 防止重复初始化
        if hasattr(self, '_initialized'):
            return
            
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.charset = charset
        self.pool_size = pool_size
        self.max_pool_size = max_pool_size
        
        self.pool: Optional[aiomysql.Pool] = None
        self.thread_pool = ThreadPoolExecutor(max_workers=thread_pool_size)
        self.logger = logging.getLogger(__name__)
        self._initialized = True
    
    async def _ensure_pool(self) -> None:
        """确保连接池已初始化（自动初始化）"""
        if self.pool is None:
            try:
                self.pool = await aiomysql.create_pool(
                    host=self.host,
                    port=self.port,
                    user=self.user,
                    password=self.password,
                    db=self.database,
                    charset=self.charset,
                    minsize=self.pool_size,
                    maxsize=self.max_pool_size,
                    autocommit=False
                )
                self.logger.info(f"MySQL连接池自动初始化成功: {self.host}:{self.port}/{self.database}")
            except Exception as e:
                self.logger.error(f"MySQL连接池自动初始化失败: {e}")
                raise
    
    async def init_pool(self) -> None:
        """手动初始化连接池（兼容旧接口）"""
        await self._ensure_pool()
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self._ensure_pool()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close_pool()
    
    def __enter__(self):
        """同步上下文管理器入口（不推荐使用）"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """同步上下文管理器出口"""
        try:
            # 尝试在当前事件循环中关闭
            loop = asyncio.get_running_loop()
            loop.create_task(self.close_pool())
        except RuntimeError:
            # 如果没有运行中的事件循环，创建新的
            try:
                asyncio.run(self.close_pool())
            except Exception as e:
                self.logger.error(f"同步上下文管理器关闭连接池失败: {e}")
    
    async def close_pool(self) -> None:
        """关闭连接池"""
        if self.pool:
            self.pool.close()
            await self.pool.wait_closed()
            self.pool = None
            self.logger.info("MySQL连接池已关闭")
        
        if hasattr(self, 'thread_pool'):
            self.thread_pool.shutdown(wait=True)
            self.logger.info("线程池已关闭")
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接的上下文管理器（自动初始化连接池）"""
        await self._ensure_pool()
        
        async with self.pool.acquire() as conn:
            try:
                yield conn
            except Exception as e:
                await conn.rollback()
                self.logger.error(f"数据库操作异常: {e}")
                raise
    
    @asynccontextmanager
    async def transaction(self):
        """事务上下文管理器"""
        async with self.get_connection() as conn:
            try:
                await conn.begin()
                yield conn
                await conn.commit()
                self.logger.debug("事务提交成功")
            except Exception as e:
                await conn.rollback()
                self.logger.error(f"事务回滚: {e}")
                raise
    
    async def execute(self, 
                     sql: str, 
                     params: Optional[Union[Tuple, Dict, List]] = None,
                     use_transaction: bool = False) -> int:
        """
        执行SQL语句（INSERT, UPDATE, DELETE等）
        
        Args:
            sql: SQL语句
            params: 参数
            use_transaction: 是否使用事务
            
        Returns:
            影响的行数
        """
        if use_transaction:
            async with self.transaction() as conn:
                async with conn.cursor() as cursor:
                    result = await cursor.execute(sql, params)
                    return result
        else:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    result = await cursor.execute(sql, params)
                    await conn.commit()
                    return result
    
    async def execute_many(self, 
                          sql: str, 
                          params_list: List[Union[Tuple, Dict]],
                          use_transaction: bool = True) -> int:
        """
        批量执行SQL语句
        
        Args:
            sql: SQL语句
            params_list: 参数列表
            use_transaction: 是否使用事务
            
        Returns:
            影响的总行数
        """
        if use_transaction:
            async with self.transaction() as conn:
                async with conn.cursor() as cursor:
                    result = await cursor.executemany(sql, params_list)
                    return result
        else:
            async with self.get_connection() as conn:
                async with conn.cursor() as cursor:
                    result = await cursor.executemany(sql, params_list)
                    await conn.commit()
                    return result
    
    async def fetch_one(self, 
                       sql: str, 
                       params: Optional[Union[Tuple, Dict]] = None) -> Optional[Dict]:
        """
        查询单条记录
        
        Args:
            sql: SQL语句
            params: 参数
            
        Returns:
            查询结果字典或None
        """
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                r = await cursor.execute(sql, params)
                return await cursor.fetchone()
    
    async def fetch_all(self, 
                       sql: str, 
                       params: Optional[Union[Tuple, Dict]] = None) -> List[Dict]:
        """
        查询多条记录
        
        Args:
            sql: SQL语句
            params: 参数
            
        Returns:
            查询结果列表
        """
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                await cursor.execute(sql, params)
                return await cursor.fetchall()
    
    async def fetch_paginated(self, 
                             sql: str, 
                             page: int = 1, 
                             page_size: int = 10,
                             params: Optional[Union[Tuple, Dict]] = None) -> Dict:
        """
        分页查询
        
        Args:
            sql: SQL语句（不含LIMIT）
            page: 页码（从1开始）
            page_size: 每页数量
            params: 参数
            
        Returns:
            包含数据和分页信息的字典
        """
        offset = (page - 1) * page_size
        paginated_sql = f"{sql} LIMIT {page_size} OFFSET {offset}"
        
        # 获取总数
        count_sql = f"SELECT COUNT(*) as total FROM ({sql}) as count_table"
        
        async with self.get_connection() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                # 查询总数
                await cursor.execute(count_sql, params)
                total_result = await cursor.fetchone()
                total = total_result['total'] if total_result else 0
                
                # 查询分页数据
                await cursor.execute(paginated_sql, params)
                data = await cursor.fetchall()
                
                return {
                    'items': data,
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total + page_size - 1) // page_size
                }
    
    async def insert(self, 
                    table: str, 
                    data: Dict[str, Any],
                    return_id: bool = True) -> Optional[int]:
        """
        插入数据
        
        Args:
            table: 表名
            data: 数据字典
            return_id: 是否返回插入ID
            
        Returns:
            插入的ID（如果return_id为True）
        """
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['%s'] * len(data))
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        async with self.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute(sql, list(data.values()))
                await conn.commit()
                
                if return_id:
                    return cursor.lastrowid
    
    async def update(self, 
                    table: str, 
                    data: Dict[str, Any], 
                    where: str, 
                    where_params: Optional[Union[Tuple, List]] = None) -> int:
        """
        更新数据
        
        Args:
            table: 表名
            data: 更新数据字典
            where: WHERE条件
            where_params: WHERE条件参数
            
        Returns:
            影响的行数
        """
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE {table} SET {set_clause} WHERE {where}"
        
        params = list(data.values())
        if where_params:
            params.extend(where_params)
        
        return await self.execute(sql, params)
    
    async def delete(self, 
                    table: str, 
                    where: str, 
                    where_params: Optional[Union[Tuple, List]] = None) -> int:
        """
        删除数据
        
        Args:
            table: 表名
            where: WHERE条件
            where_params: WHERE条件参数
            
        Returns:
            影响的行数
        """
        sql = f"DELETE FROM {table} WHERE {where}"
        return await self.execute(sql, where_params)
    
    async def run_in_thread(self, func, *args, **kwargs):
        """
        在线程池中执行函数
        
        Args:
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            函数执行结果
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, func, *args, **kwargs)
    
    async def execute_script(self, script: str) -> None:
        """
        执行SQL脚本（多条SQL语句）
        
        Args:
            script: SQL脚本内容
        """
        statements = [stmt.strip() for stmt in script.split(';') if stmt.strip()]
        
        async with self.transaction() as conn:
            async with conn.cursor() as cursor:
                for statement in statements:
                    if statement:
                        await cursor.execute(statement)
    
    async def table_exists(self, table_name: str) -> bool:
        """
        检查表是否存在
        
        Args:
            table_name: 表名
            
        Returns:
            表是否存在
        """
        sql = """
        SELECT COUNT(*) as count 
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_name = %s
        """
        result = await self.fetch_one(sql, (self.database, table_name))
        return result['count'] > 0 if result else False


# 使用示例
async def example_usage():
    """使用示例 - 自动初始化和清理"""
    
    # 创建数据库处理器（自动初始化）
    db = AsyncMySQLHandler(
        host='localhost',
        port=3306,
        user='root',
        password='your_password',
        database='your_database'
    )
    
    # 方式1: 使用异步上下文管理器（推荐）
    async with db:
        # 连接池会自动初始化
        user_id = await db.insert('users', {
            'name': '张三',
            'email': 'zhangsan@example.com',
            'age': 25
        })
        print(f"插入用户ID: {user_id}")
        
        user = await db.fetch_one("SELECT * FROM users WHERE id = %s", (user_id,))
        print(f"查询用户: {user}")
    # 连接池会自动关闭
    
    # 方式2: 直接使用（连接池自动初始化，程序退出时自动清理）
    db2 = AsyncMySQLHandler(
        host='localhost',
        port=3306,
        user='root',
        password='your_password',
        database='your_database'
    )
    
    # 第一次使用时会自动初始化连接池
    users = await db2.fetch_all("SELECT * FROM users LIMIT 5")
    print(f"所有用户: {users}")
    
    # 分页查询
    result = await db2.fetch_paginated("SELECT * FROM users", page=1, page_size=10)
    print(f"分页查询结果: {result}")
    
    # 事务示例
    async with db2.transaction() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("INSERT INTO users (name, email) VALUES (%s, %s)", 
                               ('李四', 'lisi@example.com'))
            await cursor.execute("UPDATE users SET age = %s WHERE name = %s", 
                               (30, '李四'))
    
    # 批量插入
    users_data = [
        ('王五', 'wangwu@example.com', 28),
        ('赵六', 'zhaoliu@example.com', 32)
    ]
    await db2.execute_many(
        "INSERT INTO users (name, email, age) VALUES (%s, %s, %s)",
        users_data
    )
    
    # 在线程池中执行耗时操作
    def heavy_computation(n):
        return sum(i * i for i in range(n))
    
    result = await db2.run_in_thread(heavy_computation, 10000)
    print(f"线程池计算结果: {result}")
    
    # 程序结束时连接池会自动清理，也可以手动关闭
    # await db2.close_pool()


# 简化的使用示例
async def simple_example():
    """简化的使用示例"""
    # 创建实例后直接使用，无需手动初始化
    
    db = AsyncMySQLHandler()
    
    # 直接查询，连接池会自动初始化
    users = await db.fetch_all("SELECT * FROM user WHERE username=%s", "lijiahong")
    print(users)
    
    # 分页查询
    result = await db.fetch_paginated("SELECT * FROM user", page=1, page_size=10)
    print(f"分页查询结果: {result}")
    
    # 插入数据
    # await db.insert('users', {'name': '测试用户', 'email': 'test@example.com'})
    
    # 程序结束时会自动清理资源


# if __name__ == "__main__":
    # 运行示例
    # asyncio.run(example_usage())
    
    # 或者运行简化示例
    # asyncio.run(simple_example())
    
async_db = AsyncMySQLHandler()