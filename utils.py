"""
通用工具函数模块
提供日志记录、异常处理、路径校验等功能
"""

import os
import sys
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional


class PathValidator:
    """路径校验器 - 确保使用相对路径并符合目录约束"""

    VALID_DIRECTORIES = {
        'config': './config/',
        'weather_data': './weather/data/',
        'weather_logs': './weather/logs/',
        'weather_report': './weather/report/'
    }

    @classmethod
    def validate_relative_path(cls, path: str) -> bool:
        """校验路径是否为相对路径"""
        if os.path.isabs(path):
            return False
        if path.startswith('..'):
            return False
        return True

    @classmethod
    def get_directory_path(cls, dir_type: str) -> str:
        """获取指定类型的目录路径"""
        if dir_type not in cls.VALID_DIRECTORIES:
            raise ValueError(f"无效的目录类型: {dir_type}")
        return cls.VALID_DIRECTORIES[dir_type]

    @classmethod
    def ensure_directory_exists(cls, dir_path: str) -> None:
        """确保目录存在，不存在则创建"""
        if not cls.validate_relative_path(dir_path):
            raise ValueError(f"必须使用相对路径: {dir_path}")
        Path(dir_path).mkdir(parents=True, exist_ok=True)


class LoggerManager:
    """日志管理器 - 管理日志记录和文件操作"""

    _loggers: dict = {}

    def __init__(self, log_dir: str = './weather/logs/', level: str = 'INFO'):
        self.log_dir = log_dir
        self.level = getattr(logging, level.upper(), logging.INFO)
        self._setup_log_directory()

    def _setup_log_directory(self) -> None:
        """设置日志目录"""
        PathValidator.ensure_directory_exists(self.log_dir)

    def _get_log_file_path(self) -> str:
        """获取当前日期的日志文件路径"""
        today = datetime.now().strftime('%Y%m%d')
        return os.path.join(self.log_dir, f'task_log_{today}.log')

    def get_logger(self, name: str) -> logging.Logger:
        """获取或创建日志记录器"""
        if name in self._loggers:
            return self._loggers[name]

        logger = logging.getLogger(name)
        logger.setLevel(self.level)

        # 清除现有处理器
        logger.handlers.clear()

        # 文件处理器
        file_handler = logging.FileHandler(
            self._get_log_file_path(),
            encoding='utf-8'
        )
        file_handler.setLevel(self.level)

        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.level)

        # 格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        self._loggers[name] = logger
        return logger

    def clean_old_logs(self, max_days: int = 7) -> None:
        """清理过期日志文件"""
        try:
            current_time = datetime.now()
            log_pattern = 'task_log_*.log'
            log_dir_path = Path(self.log_dir)

            for log_file in log_dir_path.glob(log_pattern):
                try:
                    file_stat = log_file.stat()
                    file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
                    days_diff = (current_time - file_mtime).days

                    if days_diff > max_days:
                        log_file.unlink()
                        print(f"已删除过期日志文件: {log_file.name}")
                except Exception as e:
                    print(f"清理日志文件失败 {log_file.name}: {str(e)}")
        except Exception as e:
            print(f"清理日志目录失败: {str(e)}")


class ExceptionHandler:
    """异常处理器 - 统一处理异常并记录"""

    @staticmethod
    def handle_exception(
        exception: Exception,
        logger: Optional[logging.Logger] = None,
        context: str = ""
    ) -> str:
        """处理异常并返回错误信息"""
        error_msg = f"{context}: {str(exception)}" if context else str(exception)
        error_detail = traceback.format_exc()

        if logger:
            logger.error(f"{error_msg}\n{error_detail}")
        else:
            print(f"[ERROR] {error_msg}")
            print(error_detail)

        return error_msg

    @staticmethod
    def validate_data_type(
        value,
        expected_type,
        field_name: str,
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """校验数据类型"""
        if not isinstance(value, expected_type):
            error_msg = f"字段 '{field_name}' 类型错误: 期望 {expected_type.__name__}, 实际 {type(value).__name__}"
            if logger:
                logger.error(error_msg)
            return False
        return True

    @staticmethod
    def validate_value_range(
        value: int,
        min_val: int,
        max_val: int,
        field_name: str,
        logger: Optional[logging.Logger] = None
    ) -> bool:
        """校验数值范围"""
        if not (min_val <= value <= max_val):
            error_msg = f"字段 '{field_name}' 超出范围: 期望 [{min_val}, {max_val}], 实际 {value}"
            if logger:
                logger.error(error_msg)
            return False
        return True


class FileNameGenerator:
    """文件名生成器 - 生成符合命名规范的文件名"""

    @staticmethod
    def generate_weather_filename(city: str, timestamp: Optional[datetime] = None) -> str:
        """生成天气数据文件名 - 以weather_开头"""
        if timestamp is None:
            timestamp = datetime.now()
        time_str = timestamp.strftime('%Y%m%d_%H%M%S')
        safe_city = city.replace(' ', '_')
        return f"weather_{safe_city}_{time_str}.json"

    @staticmethod
    def generate_log_filename(date: Optional[datetime] = None) -> str:
        """生成日志文件名 - 以task_log_开头"""
        if date is None:
            date = datetime.now()
        date_str = date.strftime('%Y%m%d')
        return f"task_log_{date_str}.log"

    @staticmethod
    def generate_report_filename(date: Optional[datetime] = None) -> str:
        """生成报告文件名"""
        if date is None:
            date = datetime.now()
        date_str = date.strftime('%Y%m%d')
        return f"weather_report_{date_str}.md"


class DataValidator:
    """数据校验器 - 校验天气数据有效性"""

    @staticmethod
    def validate_weather_data(data: dict, logger: Optional[logging.Logger] = None) -> bool:
        """校验天气数据是否有效"""
        if not isinstance(data, dict):
            if logger:
                logger.error("天气数据必须是字典类型")
            return False

        required_fields = ['city', 'temperature', 'humidity', 'condition', 'wind', 'update_time']

        for field in required_fields:
            if field not in data:
                if logger:
                    logger.error(f"天气数据缺少必要字段: {field}")
                return False

            if data[field] is None or data[field] == '':
                if logger:
                    logger.error(f"天气数据字段 '{field}' 值为空")
                return False

        # 校验温度数值范围（-50到60摄氏度）
        try:
            temp = float(data['temperature'])
            if not (-50 <= temp <= 60):
                if logger:
                    logger.error(f"温度值超出合理范围: {temp}°C")
                return False
        except (ValueError, TypeError):
            if logger:
                logger.error(f"温度值格式错误: {data['temperature']}")
            return False

        # 校验湿度数值范围（0到100%）
        try:
            humidity = float(data['humidity'])
            if not (0 <= humidity <= 100):
                if logger:
                    logger.error(f"湿度值超出合理范围: {humidity}%")
                return False
        except (ValueError, TypeError):
            if logger:
                logger.error(f"湿度值格式错误: {data['humidity']}")
            return False

        return True


class DateTimeUtil:
    """日期时间工具类"""

    @staticmethod
    def get_current_timestamp() -> str:
        """获取当前时间戳字符串"""
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def get_current_date() -> str:
        """获取当前日期字符串"""
        return datetime.now().strftime('%Y-%m-%d')

    @staticmethod
    def parse_timestamp(timestamp_str: str) -> Optional[datetime]:
        """解析时间戳字符串"""
        try:
            return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                return datetime.strptime(timestamp_str, '%Y-%m-%d')
            except ValueError:
                return None

    @staticmethod
    def format_datetime(dt: datetime, fmt: str = '%Y-%m-%d %H:%M:%S') -> str:
        """格式化日期时间"""
        return dt.strftime(fmt)
