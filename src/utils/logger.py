"""
Logging utility functions.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from src.config import LOG_DIR

def setup_logger(name: str) -> logging.Logger:
    """
    Set up a logger with both file and console handlers.
    
    Args:
        name: Name of the logger
        
    Returns:
        Configured logger instance
    """
    # 创建日志文件路径
    log_file = os.path.join(LOG_DIR, f"{name}.log")
    
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 如果日志记录器已经有处理器，直接返回
    if logger.handlers:
        return logger
    
    # 创建文件处理器
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 设置格式化器
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 添加处理器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger 