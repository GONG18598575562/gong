import requests
import time
import random
from utils import (
    log_info,
    log_error,
    log_warning,
    get_current_timestamp,
    is_valid_temperature,
    is_valid_humidity,
    clean_string,
    handle_exception
)


class WeatherFetcher:
    def __init__(self, timeout=10, retry_count=3, use_mock_fallback=True):
        self.timeout = timeout
        self.retry_count = retry_count
        self.use_mock_fallback = use_mock_fallback
        self.api_url = "https://api.seniverse.com/v3/weather/now.json"
        self.api_key = "SzgU48shIHc4WRHQv"
        self.mock_weather_conditions = ["晴", "多云", "阴", "小雨", "中雨", "大雨", "雷阵雨", "微风", "雾"]
        self.mock_wind_directions = ["东", "南", "西", "北", "东北", "东南", "西北", "西南"]

    def fetch_raw_data(self, city):
        for attempt in range(self.retry_count):
            try:
                params = {
                    "key": self.api_key,
                    "location": city,
                    "language": "zh-Hans",
                    "unit": "c"
                }
                response = requests.get(
                    self.api_url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                return response.json()
            except requests.RequestException as e:
                if attempt < self.retry_count - 1:
                    log_warning(f"获取 [{city}] 天气失败，重试 {attempt + 1}/{self.retry_count}: {str(e)}")
                    time.sleep(2)
                else:
                    log_error(f"获取 [{city}] 天气失败，已达到最大重试次数: {str(e)}")
                    if self.use_mock_fallback:
                        log_info(f"使用模拟数据模式获取 [{city}] 天气")
                        return self._generate_mock_data(city)
        return None

    def _generate_mock_data(self, city):
        return {
            "results": [{
                "location": {"name": city},
                "now": {
                    "temperature": random.randint(5, 35),
                    "humidity": random.randint(30, 95),
                    "text": random.choice(self.mock_weather_conditions),
                    "wind_direction": random.choice(self.mock_wind_directions),
                    "wind_scale": random.randint(1, 6)
                }
            }]
        }

    def clean_weather_data(self, raw_data, city):
        try:
            if not raw_data or "results" not in raw_data:
                log_error(f"[{city}] 返回数据格式无效")
                return None

            results = raw_data["results"]
            if not results or len(results) == 0:
                log_error(f"[{city}] 没有天气数据结果")
                return None

            weather_now = results[0].get("now", {})
            location_data = results[0].get("location", {})

            temperature = weather_now.get("temperature")
            humidity = weather_now.get("humidity")
            weather_text = weather_now.get("text", "")
            wind_direction = weather_now.get("wind_direction", "")
            wind_scale = weather_now.get("wind_scale", "")

            cleaned_data = {
                "city": clean_string(location_data.get("name", city)),
                "temperature": None,
                "humidity": None,
                "weather_condition": clean_string(weather_text),
                "wind_power": clean_string(f"{wind_direction}风 {wind_scale}级"),
                "update_time": get_current_timestamp(),
                "is_valid": False
            }

            if is_valid_temperature(temperature):
                cleaned_data["temperature"] = float(temperature)
            else:
                log_warning(f"[{city}] 温度数据异常: {temperature}")
                return None

            if is_valid_humidity(humidity):
                cleaned_data["humidity"] = float(humidity)
            else:
                log_warning(f"[{city}] 湿度数据异常: {humidity}")
                return None

            if not cleaned_data["weather_condition"]:
                cleaned_data["weather_condition"] = "未知"

            cleaned_data["is_valid"] = True
            return cleaned_data

        except Exception as e:
            handle_exception(e, f"清洗 [{city}] 天气数据时")
            return None

    def fetch_city_weather(self, city):
        log_info(f"正在获取 [{city}] 的天气数据")
        raw_data = self.fetch_raw_data(city)
        if not raw_data:
            return None

        cleaned_data = self.clean_weather_data(raw_data, city)
        if cleaned_data and cleaned_data["is_valid"]:
            log_info(f"[{city}] 天气数据获取并清洗成功")
            return cleaned_data
        else:
            log_error(f"[{city}] 天气数据清洗失败")
            return None

    def fetch_multiple_cities(self, cities):
        weather_data_list = []
        log_info(f"开始批量获取天气数据，城市数量: {len(cities)}")

        for city in cities:
            weather_data = self.fetch_city_weather(city)
            if weather_data:
                weather_data_list.append(weather_data)
            else:
                log_warning(f"跳过无效的城市天气数据: {city}")
            time.sleep(1)

        log_info(f"批量获取完成，成功获取 {len(weather_data_list)}/{len(cities)} 个城市的天气数据")
        return weather_data_list
