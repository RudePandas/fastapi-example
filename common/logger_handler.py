import logging
import os
from logging.handlers import TimedRotatingFileHandler

def setup_logger():
    # 确保日志目录存在
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 格式化器
    formatter = logging.Formatter(
        '[%(asctime)s][%(levelname)s][%(filename)s:%(lineno)d][%(thread)d] %(message)s'
    )
    
    # 获取logger
    logger = logging.getLogger('app')
    logger.setLevel(logging.DEBUG)
    
    # 文件处理器
    file_handler = TimedRotatingFileHandler(
        'logs/app.log', 
        when='midnight', 
        backupCount=7, 
        encoding='utf8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)  # 文件只记录INFO及以上
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG)  # 开发时显示所有日志
    
    # 避免重复添加handler
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger

# 使用
app_logger = setup_logger()