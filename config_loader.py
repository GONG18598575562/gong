"""
配置加载模块
加载并校验YAML配置文件，读取城市白名单（只读）
"""

import os
import yaml
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from utils import PathValidator, ExceptionHandler, LoggerManager


class ConfigLoader:
    """配置加载器 - 加载和校验用户配置"""

    CONFIG_PATH = './config/config.yaml'
    WHITE_LIST_PATH = './config/city_white_list.yaml'

    def __init__(self):
        self.logger_manager = LoggerManager()
        self.logger = self.logger_manager.get_logger('ConfigLoader')
        self.config: Dict[str, Any] = {}
        self.city_white_list: List[str] = []
        self._load_white_list()

    def _load_white_list(self) -> None:
        """加载城市白名单（只读）"""
        try:
            if not PathValidator.validate_relative_path(self.WHITE_LIST_PATH):
                raise ValueError(f"白名单路径必须使用相对路径: {self.WHITE_LIST_PATH}")

            if not os.path.exists(self.WHITE_LIST_PATH):
                raise FileNotFoundError(f"城市白名单文件不存在: {self.WHITE_LIST_PATH}")

            with open(self.WHITE_LIST_PATH, 'r', encoding='utf-8') as f:
                white_list_data = yaml.safe_load(f)

            if not white_list_data or 'city_white_list' not in white_list_data:
                raise ValueError("城市白名单文件格式错误，缺少'city_white_list'字段")

            self.city_white_list = white_list_data['city_white_list']

            if not isinstance(self.city_white_list, list) or len(self.city_white_list) == 0:
                raise ValueError("城市白名单不能为空")

            self.logger.info(f"成功加载城市白名单，共 {len(self.city_white_list)} 个城市")

        except Exception as e:
            ExceptionHandler.handle_exception(e, self.logger, "加载城市白名单失败")
            raise

    def load_config(self) -> Dict[str, Any]:
        """加载用户配置文件"""
        try:
            if not PathValidator.validate_relative_path(self.CONFIG_PATH):
                raise ValueError(f"配置文件路径必须使用相对路径: {self.CONFIG_PATH}")

            if not os.path.exists(self.CONFIG_PATH):
                raise FileNotFoundError(f"配置文件不存在: {self.CONFIG_PATH}")

            with open(self.CONFIG_PATH, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)

            if not self.config:
                raise ValueError("配置文件为空")

            self.logger.info("成功加载用户配置文件")
            return self.config

        except Exception as e:
            ExceptionHandler.handle_exception(e, self.logger, "加载配置文件失败")
            raise

    def validate_config(self) -> bool:
        """校验配置合法性"""
        try:
            errors = []

            # 校验定时任务配置
            if 'schedule' not in self.config:
                errors.append("缺少'schedule'配置")
            else:
                schedule = self.config['schedule']
                if 'interval_minutes' not in schedule:
                    errors.append("缺少'schedule.interval_minutes'配置")
                else:
                    interval = schedule['interval_minutes']
                    if not isinstance(interval, int) or not (1 <= interval <= 1440):
                        errors.append(f"'interval_minutes'必须是1-1440的整数，当前值: {interval}")

            # 校验目标城市配置
            if 'target_cities' not in self.config:
                errors.append("缺少'target_cities'配置")
            else:
                cities = self.config['target_cities']
                if not isinstance(cities, list):
                    errors.append("'target_cities'必须是列表")
                elif len(cities) == 0:
                    errors.append("'target_cities'不能为空")
                elif len(cities) > 5:
                    errors.append(f"'target_cities'最多配置5个城市，当前: {len(cities)}")
                else:
                    # 校验城市是否在白名单中
                    for city in cities:
                        if city not in self.city_white_list:
                            errors.append(f"城市 '{city}' 不在白名单中")

            # 校验天气API配置
            if 'weather_api' not in self.config:
                errors.append("缺少'weather_api'配置")
            else:
                api_config = self.config['weather_api']
                if 'base_url' not in api_config:
                    errors.append("缺少'weather_api.base_url'配置")
                if 'timeout_seconds' not in api_config:
                    errors.append("缺少'weather_api.timeout_seconds'配置")
                if 'retry_times' not in api_config:
                    errors.append("缺少'weather_api.retry_times'配置")

            # 校验日志配置
            if 'logging' not in self.config:
                errors.append("缺少'logging'配置")
            else:
                log_config = self.config['logging']
                if 'level' not in log_config:
                    errors.append("缺少'logging.level'配置")
                else:
                    valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
                    if log_config['level'] not in valid_levels:
                        errors.append(f"日志级别必须是 {valid_levels} 之一")

            # 校验存储配置
            if 'storage' not in self.config:
                errors.append("缺少'storage'配置")

            if errors:
                for error in errors:
                    self.logger.error(f"配置校验错误: {error}")
                return False

            self.logger.info("配置校验通过")
            return True

        except Exception as e:
            ExceptionHandler.handle_exception(e, self.logger, "配置校验失败")
            return False

    def get_schedule_interval(self) -> int:
        """获取定时任务间隔（分钟）"""
        return self.config.get('schedule', {}).get('interval_minutes', 30)

    def get_target_cities(self) -> List[str]:
        """获取目标城市列表"""
        return self.config.get('target_cities', [])

    def get_weather_api_config(self) -> Dict[str, Any]:
        """获取天气API配置"""
        return self.config.get('weather_api', {})

    def get_logging_config(self) -> Dict[str, Any]:
        """获取日志配置"""
        return self.config.get('logging', {})

    def get_storage_config(self) -> Dict[str, Any]:
        """获取存储配置"""
        return self.config.get('storage', {})

    def get_city_white_list(self) -> List[str]:
        """获取城市白名单（只读）"""
        return self.city_white_list.copy()

    def is_city_valid(self, city: str) -> bool:
        """检查城市是否在白名单中"""
        return city in self.city_white_list


class ConfigManager:
    """配置管理器 - 统一管理配置加载和访问"""

    _instance: Optional['ConfigManager'] = None
    _config_loader: Optional[ConfigLoader] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def initialize(self) -> bool:
        """初始化配置管理器"""
        try:
            self._config_loader = ConfigLoader()
            self._config_loader.load_config()
            return self._config_loader.validate_config()
        except Exception as e:
            logging.error(f"配置管理器初始化失败: {str(e)}")
            return False

    def get_config_loader(self) -> ConfigLoader:
        """获取配置加载器"""
        if self._config_loader is None:
            raise RuntimeError("配置管理器未初始化")
        return self._config_loader

    def reload_config(self) -> bool:
        """重新加载配置"""
        if self._config_loader is None:
            return self.initialize()

        try:
            self._config_loader.load_config()
            return self._config_loader.validate_config()
        except Exception as e:
            logging.error(f"重新加载配置失败: {str(e)}")
            return False
