import os
import yaml
from typing import Dict, List, Optional, Any
from utils import LoggerManager, PathValidator, ExceptionHandler


class ConfigLoader:
    
    def __init__(self, config_dir: str = './config/'):
        self.config_dir = config_dir
        self.logger = LoggerManager.get_logger('ConfigLoader')
        self._white_list_cache: Optional[List[str]] = None
    
    def load_yaml_config(self, filename: str) -> Optional[Dict[str, Any]]:
        file_path = os.path.join(self.config_dir, filename)
        
        if not PathValidator.validate_relative_path(file_path):
            self.logger.error(f'配置文件路径不合法: {file_path}')
            return None
        
        if not os.path.exists(file_path):
            self.logger.error(f'配置文件不存在: {file_path}')
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config if config else {}
        except yaml.YAMLError as e:
            ExceptionHandler.handle_exception(self.logger, e, f'YAML解析错误 {file_path}')
            return None
        except Exception as e:
            ExceptionHandler.handle_exception(self.logger, e, f'读取配置文件失败 {file_path}')
            return None
    
    def load_city_white_list(self) -> List[str]:
        if self._white_list_cache is not None:
            return self._white_list_cache
        
        white_list_config = self.load_yaml_config('city_white_list.yaml')
        
        if white_list_config is None:
            self.logger.warning('城市白名单配置文件不存在或为空,使用默认白名单')
            self._white_list_cache = ['北京', '上海', '广州', '深圳', '杭州']
            return self._white_list_cache
        
        white_list = white_list_config.get('cities', [])
        
        if not isinstance(white_list, list):
            self.logger.error('城市白名单格式错误,必须为列表')
            self._white_list_cache = []
            return self._white_list_cache
        
        self._white_list_cache = [str(city) for city in white_list if city]
        self.logger.info(f'加载城市白名单成功,共{len(self._white_list_cache)}个城市')
        return self._white_list_cache
    
    def validate_city_in_white_list(self, city: str) -> bool:
        white_list = self.load_city_white_list()
        return city in white_list
    
    def load_app_config(self) -> Optional[Dict[str, Any]]:
        config = self.load_yaml_config('config.yaml')
        
        if config is None:
            self.logger.error('应用配置文件加载失败')
            return None
        
        validation_result = self._validate_config(config)
        
        if not validation_result['valid']:
            self.logger.error(f'配置校验失败: {validation_result["errors"]}')
            return None
        
        self.logger.info('应用配置加载并校验成功')
        return config
    
    def _validate_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        result = {'valid': True, 'errors': []}
        
        if 'cities' not in config:
            result['errors'].append('缺少cities配置项')
            result['valid'] = False
        else:
            cities = config['cities']
            if not isinstance(cities, list):
                result['errors'].append('cities必须为列表')
                result['valid'] = False
            elif len(cities) < 1 or len(cities) > 5:
                result['errors'].append('cities数量必须在1-5个之间')
                result['valid'] = False
            else:
                invalid_cities = []
                for city in cities:
                    if not self.validate_city_in_white_list(str(city)):
                        invalid_cities.append(str(city))
                if invalid_cities:
                    result['errors'].append(f'以下城市不在白名单中: {", ".join(invalid_cities)}')
                    result['valid'] = False
        
        if 'schedule' not in config:
            result['errors'].append('缺少schedule配置项')
            result['valid'] = False
        else:
            schedule = config['schedule']
            if not isinstance(schedule, dict):
                result['errors'].append('schedule必须为字典')
                result['valid'] = False
            else:
                interval = schedule.get('interval_minutes')
                if interval is None:
                    result['errors'].append('缺少interval_minutes配置项')
                    result['valid'] = False
                elif not isinstance(interval, (int, float)) or interval <= 0:
                    result['errors'].append('interval_minutes必须为正数')
                    result['valid'] = False
        
        if 'api' not in config:
            result['errors'].append('缺少api配置项')
            result['valid'] = False
        else:
            api = config['api']
            if not isinstance(api, dict):
                result['errors'].append('api必须为字典')
                result['valid'] = False
            elif 'url' not in api:
                result['errors'].append('缺少api.url配置项')
                result['valid'] = False
            elif 'key' not in api:
                result['errors'].append('缺少api.key配置项')
                result['valid'] = False
        
        return result


class ConfigValidator:
    
    @staticmethod
    def validate_all_paths() -> bool:
        required_dirs = [
            './config/',
            './weather/data/',
            './weather/logs/',
            './weather/report/'
        ]
        
        for dir_path in required_dirs:
            if not PathValidator.ensure_directory_exists(dir_path):
                return False
        return True
