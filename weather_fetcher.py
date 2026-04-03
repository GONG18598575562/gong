import requests
from typing import Dict, Optional, Any
from datetime import datetime
from utils import LoggerManager, ExceptionHandler


class WeatherFetcher:
    
    def __init__(self, api_config: Dict[str, Any]):
        self.api_url = api_config.get('url', '')
        self.api_key = api_config.get('key', '')
        self.timeout = api_config.get('timeout', 10)
        self.logger = LoggerManager.get_logger('WeatherFetcher')
    
    def fetch_weather(self, city: str) -> Optional[Dict[str, Any]]:
        try:
            params = {
                'city': city,
                'key': self.api_key
            }
            
            response = requests.get(
                self.api_url,
                params=params,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                self.logger.error(f'获取{city}天气失败,HTTP状态码: {response.status_code}')
                return None
            
            data = response.json()
            weather_data = self._parse_weather_data(city, data)
            
            if weather_data:
                self.logger.info(f'成功获取{city}天气数据')
                return weather_data
            else:
                self.logger.warning(f'{city}天气数据解析失败')
                return None
                
        except requests.exceptions.Timeout:
            ExceptionHandler.log_and_skip(self.logger, Exception('请求超时'), f'获取{city}天气')
            return None
        except requests.exceptions.RequestException as e:
            ExceptionHandler.log_and_skip(self.logger, e, f'获取{city}天气')
            return None
        except Exception as e:
            ExceptionHandler.log_and_skip(self.logger, e, f'获取{city}天气')
            return None
    
    def _parse_weather_data(self, city: str, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            if not self._validate_raw_data(raw_data):
                return None
            
            weather_info = raw_data.get('data', {})
            
            weather_data = {
                'city': city,
                'temperature': self._safe_get_float(weather_info, 'temperature'),
                'humidity': self._safe_get_int(weather_info, 'humidity'),
                'weather_condition': weather_info.get('weather', '未知'),
                'wind_power': weather_info.get('windpower', '未知'),
                'update_time': weather_info.get('reporttime', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            if not self._validate_weather_data(weather_data):
                return None
            
            return weather_data
            
        except Exception as e:
            ExceptionHandler.log_and_skip(self.logger, e, f'解析{city}天气数据')
            return None
    
    def _validate_raw_data(self, data: Dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False
        
        if 'status' in data and data['status'] != '1':
            return False
        
        if 'data' not in data:
            return False
        
        return True
    
    def _validate_weather_data(self, data: Dict[str, Any]) -> bool:
        if not data:
            return False
        
        required_fields = ['city', 'temperature', 'humidity', 'weather_condition']
        for field in required_fields:
            if field not in data:
                return False
        
        if data['temperature'] is None or data['temperature'] < -100 or data['temperature'] > 100:
            return False
        
        if data['humidity'] is None or data['humidity'] < 0 or data['humidity'] > 100:
            return False
        
        return True
    
    def _safe_get_float(self, data: Dict[str, Any], key: str) -> Optional[float]:
        try:
            value = data.get(key)
            if value is None:
                return None
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _safe_get_int(self, data: Dict[str, Any], key: str) -> Optional[int]:
        try:
            value = data.get(key)
            if value is None:
                return None
            return int(float(value))
        except (ValueError, TypeError):
            return None


class DataCleaner:
    
    @staticmethod
    def clean_weather_data(weather_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not weather_data:
            return None
        
        cleaned_data = weather_data.copy()
        
        if 'temperature' in cleaned_data:
            cleaned_data['temperature'] = DataCleaner._clean_temperature(cleaned_data['temperature'])
        
        if 'humidity' in cleaned_data:
            cleaned_data['humidity'] = DataCleaner._clean_humidity(cleaned_data['humidity'])
        
        if 'weather_condition' in cleaned_data:
            cleaned_data['weather_condition'] = DataCleaner._clean_weather_condition(cleaned_data['weather_condition'])
        
        if 'wind_power' in cleaned_data:
            cleaned_data['wind_power'] = DataCleaner._clean_wind_power(cleaned_data['wind_power'])
        
        return cleaned_data
    
    @staticmethod
    def _clean_temperature(temp: Any) -> Optional[float]:
        try:
            temp_float = float(temp)
            if -100 <= temp_float <= 100:
                return round(temp_float, 1)
            return None
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _clean_humidity(humidity: Any) -> Optional[int]:
        try:
            humidity_int = int(float(humidity))
            if 0 <= humidity_int <= 100:
                return humidity_int
            return None
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def _clean_weather_condition(condition: Any) -> str:
        if not condition:
            return '未知'
        condition_str = str(condition).strip()
        if not condition_str:
            return '未知'
        return condition_str
    
    @staticmethod
    def _clean_wind_power(wind: Any) -> str:
        if not wind:
            return '未知'
        wind_str = str(wind).strip()
        if not wind_str:
            return '未知'
        return wind_str
