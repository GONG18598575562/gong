import os
import logging
from datetime import datetime
from typing import Optional


class PathValidator:
    
    @staticmethod
    def validate_relative_path(path: str) -> bool:
        if not path:
            return False
        if os.path.isabs(path):
            return False
        if '..' in path:
            return False
        return True
    
    @staticmethod
    def ensure_directory_exists(dir_path: str) -> bool:
        if not PathValidator.validate_relative_path(dir_path):
            return False
        try:
            os.makedirs(dir_path, exist_ok=True)
            return True
        except Exception:
            return False


class LoggerManager:
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: str, log_dir: str = './weather/logs/') -> logging.Logger:
        if name in cls._loggers:
            return cls._loggers[name]
        
        PathValidator.ensure_directory_exists(log_dir)
        
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)
        
        if logger.handlers:
            logger.handlers.clear()
        
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f'task_log_{datetime.now().strftime("%Y%m%d")}.log'),
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        cls._loggers[name] = logger
        return logger


class ExceptionHandler:
    
    @staticmethod
    def handle_exception(logger: logging.Logger, exception: Exception, context: str = '') -> None:
        error_message = f'{context}: {str(exception)}' if context else str(exception)
        logger.error(error_message, exc_info=True)
    
    @staticmethod
    def log_and_skip(logger: logging.Logger, exception: Exception, context: str = '') -> None:
        error_message = f'{context}: {str(exception)}' if context else str(exception)
        logger.warning(f'跳过异常数据 - {error_message}')


def get_current_timestamp() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def format_filename(prefix: str, timestamp: Optional[str] = None, extension: str = '') -> str:
    if timestamp is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'{prefix}{timestamp}'
    if extension:
        if not extension.startswith('.'):
            extension = f'.{extension}'
        filename += extension
    return filename


def safe_write_file(file_path: str, content: str, logger: logging.Logger) -> bool:
    try:
        dir_path = os.path.dirname(file_path)
        if dir_path:
            PathValidator.ensure_directory_exists(dir_path)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        ExceptionHandler.handle_exception(logger, e, f'写入文件失败 {file_path}')
        return False


def safe_read_file(file_path: str, logger: logging.Logger) -> Optional[str]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        ExceptionHandler.handle_exception(logger, e, f'读取文件失败 {file_path}')
        return None
