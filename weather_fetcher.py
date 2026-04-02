"""
天气数据获取模块
调用天气接口，获取并清洗原始天气数据
"""

import re
import json
import time
import urllib.request
import urllib.error
from typing import Dict, Any, Optional, List
from datetime import datetime

from utils import (
    LoggerManager,
    ExceptionHandler,
    DataValidator,
    DateTimeUtil
)


class WeatherFetcher:
    """天气数据获取器 - 从API获取并清洗天气数据"""

    def __init__(self, api_config: Dict[str, Any]):
        self.logger_manager = LoggerManager()
        self.logger = self.logger_manager.get_logger('WeatherFetcher')
        self.api_config = api_config
        self.base_url = api_config.get('base_url', 'https://wttr.in')
        self.timeout = api_config.get('timeout_seconds', 10)
        self.retry_times = api_config.get('retry_times', 3)

    def fetch_weather(self, city: str) -> Optional[Dict[str, Any]]:
        """获取指定城市的天气数据"""
        self.logger.info(f"开始获取城市 '{city}' 的天气数据")

        for attempt in range(self.retry_times):
            try:
                raw_data = self._call_api(city)
                if raw_data:
                    cleaned_data = self._clean_data(raw_data, city)
                    if cleaned_data and DataValidator.validate_weather_data(cleaned_data, self.logger):
                        self.logger.info(f"成功获取并校验城市 '{city}' 的天气数据")
                        return cleaned_data
                    else:
                        self.logger.warning(f"城市 '{city}' 的数据校验失败，跳过")
                        return None
                else:
                    self.logger.warning(f"城市 '{city}' 的API返回空数据")
                    return None

            except Exception as e:
                ExceptionHandler.handle_exception(
                    e, self.logger, f"获取城市 '{city}' 天气数据失败（尝试 {attempt + 1}/{self.retry_times}）"
                )
                if attempt < self.retry_times - 1:
                    time.sleep(1)  # 重试前等待1秒
                else:
                    self.logger.error(f"城市 '{city}' 的天气数据获取最终失败")
                    return None

        return None

    def _call_api(self, city: str) -> Optional[Dict[str, Any]]:
        """调用天气API获取原始数据"""
        try:
            # 使用 wttr.in API，返回JSON格式
            encoded_city = urllib.parse.quote(city)
            url = f"{self.base_url}/{encoded_city}?format=j1"

            self.logger.debug(f"请求URL: {url}")

            req = urllib.request.Request(
                url,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0'
                }
            )

            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    return data
                else:
                    self.logger.error(f"API返回非200状态码: {response.status}")
                    return None

        except urllib.error.HTTPError as e:
            self.logger.error(f"HTTP错误: {e.code} - {e.reason}")
            return None
        except urllib.error.URLError as e:
            self.logger.error(f"URL错误: {e.reason}")
            return None
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON解析错误: {str(e)}")
            return None
        except Exception as e:
            ExceptionHandler.handle_exception(e, self.logger, "API调用异常")
            return None

    def _clean_data(self, raw_data: Dict[str, Any], city: str) -> Optional[Dict[str, Any]]:
        """清洗和格式化原始天气数据"""
        try:
            if not raw_data or 'current_condition' not in raw_data:
                self.logger.error("原始数据格式错误，缺少'current_condition'")
                return None

            current = raw_data.get('current_condition', [{}])[0]

            if not current:
                self.logger.error("当前天气数据为空")
                return None

            # 提取温度
            temperature = self._extract_temperature(current)

            # 提取湿度
            humidity = self._extract_humidity(current)

            # 提取天气状况
            condition = self._extract_condition(current)

            # 提取风力
            wind = self._extract_wind(current)

            # 获取更新时间
            update_time = DateTimeUtil.get_current_timestamp()

            cleaned_data = {
                'city': city,
                'temperature': temperature,
                'humidity': humidity,
                'condition': condition,
                'wind': wind,
                'update_time': update_time,
                'raw_data': raw_data  # 保留原始数据用于调试
            }

            self.logger.debug(f"清洗后的数据: {cleaned_data}")
            return cleaned_data

        except Exception as e:
            ExceptionHandler.handle_exception(e, self.logger, "数据清洗失败")
            return None

    def _extract_temperature(self, current: Dict[str, Any]) -> Optional[float]:
        """提取温度数据"""
        try:
            # 优先使用摄氏度
            temp_c = current.get('temp_C')
            if temp_c is not None:
                return float(temp_c)

            temp_c = current.get('tempC')
            if temp_c is not None:
                return float(temp_c)

            # 备选：从华氏度转换
            temp_f = current.get('temp_F')
            if temp_f is not None:
                return round((float(temp_f) - 32) * 5 / 9, 1)

            self.logger.warning("无法提取温度数据")
            return None

        except (ValueError, TypeError) as e:
            self.logger.error(f"温度数据转换错误: {str(e)}")
            return None

    def _extract_humidity(self, current: Dict[str, Any]) -> Optional[float]:
        """提取湿度数据"""
        try:
            humidity = current.get('humidity')
            if humidity is not None:
                return float(humidity)

            self.logger.warning("无法提取湿度数据")
            return None

        except (ValueError, TypeError) as e:
            self.logger.error(f"湿度数据转换错误: {str(e)}")
            return None

    def _extract_condition(self, current: Dict[str, Any]) -> str:
        """提取天气状况"""
        try:
            # 优先使用中文描述
            lang_cn = current.get('lang_zh', [{}])[0]
            if lang_cn and 'value' in lang_cn:
                return lang_cn['value']

            # 备选：英文描述
            weather_desc = current.get('weatherDesc', [{}])[0]
            if weather_desc and 'value' in weather_desc:
                return weather_desc['value']

            # 备选：weatherCode
            weather_code = current.get('weatherCode')
            if weather_code:
                return self._get_weather_description(weather_code)

            return "未知"

        except Exception as e:
            self.logger.error(f"天气状况提取错误: {str(e)}")
            return "未知"

    def _extract_wind(self, current: Dict[str, Any]) -> str:
        """提取风力数据"""
        try:
            wind_speed = current.get('windspeedKmph')
            wind_dir = current.get('winddir16Point', '')

            if wind_speed is not None:
                return f"{wind_dir} {wind_speed}km/h"

            wind_speed_miles = current.get('windspeedMiles')
            if wind_speed_miles is not None:
                speed_kmph = round(float(wind_speed_miles) * 1.609, 1)
                return f"{wind_dir} {speed_kmph}km/h"

            return "未知"

        except (ValueError, TypeError) as e:
            self.logger.error(f"风力数据提取错误: {str(e)}")
            return "未知"

    def _get_weather_description(self, code: str) -> str:
        """根据天气代码获取描述"""
        weather_codes = {
            '113': '晴朗',
            '116': '多云',
            '119': '阴天',
            '122': '阴天',
            '143': '雾',
            '176': '小雨',
            '179': '雨夹雪',
            '182': '雨夹雪',
            '185': '冻雨',
            '200': '雷阵雨',
            '227': '阵雪',
            '230': '大雪',
            '248': '雾',
            '260': '冻雾',
            '263': '小雨',
            '266': '小雨',
            '281': '冻雨',
            '284': '冻雨',
            '293': '小雨',
            '296': '小雨',
            '299': '中雨',
            '302': '中雨',
            '305': '大雨',
            '308': '大雨',
            '311': '冻雨',
            '314': '冻雨',
            '317': '雨夹雪',
            '320': '大雪',
            '323': '阵雪',
            '326': '阵雪',
            '329': '大雪',
            '332': '大雪',
            '335': '暴雪',
            '338': '暴雪',
            '350': '冰雹',
            '353': '阵雨',
            '356': '雷阵雨',
            '359': '暴雨',
            '362': '雨夹雪',
            '365': '雨夹雪',
            '368': '阵雪',
            '371': '大雪',
            '374': '冰雹',
            '377': '冰雹',
            '386': '雷阵雨',
            '389': '雷暴',
            '392': '雷阵雨',
            '395': '暴雪'
        }
        return weather_codes.get(code, '未知')


class WeatherDataProcessor:
    """天气数据处理器 - 批量处理多个城市的天气数据"""

    def __init__(self, api_config: Dict[str, Any]):
        self.logger_manager = LoggerManager()
        self.logger = self.logger_manager.get_logger('WeatherDataProcessor')
        self.fetcher = WeatherFetcher(api_config)

    def fetch_multiple_cities(self, cities: List[str]) -> List[Dict[str, Any]]:
        """批量获取多个城市的天气数据"""
        results = []
        valid_cities = []

        # 过滤无效城市
        for city in cities:
            if city and isinstance(city, str):
                valid_cities.append(city)
            else:
                self.logger.warning(f"跳过无效城市名称: {city}")

        self.logger.info(f"开始批量获取 {len(valid_cities)} 个城市的天气数据")

        for city in valid_cities:
            try:
                weather_data = self.fetcher.fetch_weather(city)
                if weather_data:
                    results.append(weather_data)
                else:
                    self.logger.warning(f"城市 '{city}' 的数据获取失败，跳过该城市")
            except Exception as e:
                ExceptionHandler.handle_exception(
                    e, self.logger, f"处理城市 '{city}' 时发生异常"
                )
                continue

        self.logger.info(f"成功获取 {len(results)}/{len(valid_cities)} 个城市的天气数据")
        return results

    def filter_invalid_data(self, data_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤无效/异常的天气数据"""
        valid_data = []

        for data in data_list:
            try:
                if DataValidator.validate_weather_data(data, self.logger):
                    valid_data.append(data)
                else:
                    self.logger.warning(f"数据校验失败，城市: {data.get('city', '未知')}")
            except Exception as e:
                self.logger.error(f"数据过滤异常: {str(e)}")
                continue

        self.logger.info(f"数据过滤完成: {len(valid_data)}/{len(data_list)} 条有效")
        return valid_data
