import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from utils import LoggerManager, PathValidator, format_filename, safe_write_file


class DataSaver:
    
    def __init__(self, data_dir: str = './weather/data/', report_dir: str = './weather/report/'):
        self.data_dir = data_dir
        self.report_dir = report_dir
        self.logger = LoggerManager.get_logger('DataSaver')
    
    def save_weather_data(self, weather_data: Dict[str, Any]) -> bool:
        if not weather_data:
            self.logger.warning('天气数据为空,跳过保存')
            return False
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = format_filename('weather_', timestamp, '.json')
        file_path = os.path.join(self.data_dir, filename)
        
        try:
            PathValidator.ensure_directory_exists(self.data_dir)
            
            json_content = json.dumps(weather_data, ensure_ascii=False, indent=2)
            
            if safe_write_file(file_path, json_content, self.logger):
                self.logger.info(f'天气数据保存成功: {file_path}')
                return True
            return False
            
        except Exception as e:
            self.logger.error(f'保存天气数据失败: {str(e)}')
            return False
    
    def save_batch_weather_data(self, weather_list: List[Dict[str, Any]]) -> bool:
        if not weather_list:
            self.logger.warning('批量天气数据为空,跳过保存')
            return False
        
        batch_data = {
            'fetch_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'city_count': len(weather_list),
            'weather_data': weather_list
        }
        
        return self.save_weather_data(batch_data)


class ReportGenerator:
    
    def __init__(self, report_dir: str = './weather/report/'):
        self.report_dir = report_dir
        self.logger = LoggerManager.get_logger('ReportGenerator')
    
    def generate_daily_report(self, weather_list: List[Dict[str, Any]]) -> bool:
        if not weather_list:
            self.logger.warning('天气数据为空,跳过报告生成')
            return False
        
        report_content = self._build_report_content(weather_list)
        
        date_str = datetime.now().strftime('%Y%m%d')
        filename = format_filename('weather_report_', date_str, '.md')
        file_path = os.path.join(self.report_dir, filename)
        
        if safe_write_file(file_path, report_content, self.logger):
            self.logger.info(f'天气报告生成成功: {file_path}')
            return True
        return False
    
    def _build_report_content(self, weather_list: List[Dict[str, Any]]) -> str:
        report_lines = []
        
        report_lines.append(f'# 每日天气汇总报告')
        report_lines.append('')
        report_lines.append(f'**生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        report_lines.append(f'**城市数量**: {len(weather_list)}')
        report_lines.append('')
        report_lines.append('---')
        report_lines.append('')
        report_lines.append('## 天气详情')
        report_lines.append('')
        
        for idx, weather in enumerate(weather_list, 1):
            report_lines.append(f'### {idx}. {weather.get("city", "未知城市")}')
            report_lines.append('')
            report_lines.append(f'- **温度**: {weather.get("temperature", "未知")}°C')
            report_lines.append(f'- **湿度**: {weather.get("humidity", "未知")}%')
            report_lines.append(f'- **天气状况**: {weather.get("weather_condition", "未知")}')
            report_lines.append(f'- **风力**: {weather.get("wind_power", "未知")}')
            report_lines.append(f'- **更新时间**: {weather.get("update_time", "未知")}')
            report_lines.append('')
        
        report_lines.append('---')
        report_lines.append('')
        report_lines.append('## 统计信息')
        report_lines.append('')
        
        stats = self._calculate_statistics(weather_list)
        report_lines.append(f'- **平均温度**: {stats["avg_temp"]}°C')
        report_lines.append(f'- **最高温度**: {stats["max_temp"]}°C')
        report_lines.append(f'- **最低温度**: {stats["min_temp"]}°C')
        report_lines.append(f'- **平均湿度**: {stats["avg_humidity"]}%')
        report_lines.append('')
        
        return '\n'.join(report_lines)
    
    def _calculate_statistics(self, weather_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        temps = [w.get('temperature') for w in weather_list if w.get('temperature') is not None]
        humidities = [w.get('humidity') for w in weather_list if w.get('humidity') is not None]
        
        stats = {
            'avg_temp': '未知',
            'max_temp': '未知',
            'min_temp': '未知',
            'avg_humidity': '未知'
        }
        
        if temps:
            stats['avg_temp'] = round(sum(temps) / len(temps), 1)
            stats['max_temp'] = max(temps)
            stats['min_temp'] = min(temps)
        
        if humidities:
            stats['avg_humidity'] = round(sum(humidities) / len(humidities), 1)
        
        return stats


class WeatherDataManager:
    
    def __init__(self):
        self.data_saver = DataSaver()
        self.report_generator = ReportGenerator()
        self.logger = LoggerManager.get_logger('WeatherDataManager')
    
    def process_and_save(self, weather_list: List[Dict[str, Any]]) -> bool:
        if not weather_list:
            self.logger.warning('没有有效天气数据需要处理')
            return False
        
        save_result = self.data_saver.save_batch_weather_data(weather_list)
        
        report_result = self.report_generator.generate_daily_report(weather_list)
        
        if save_result and report_result:
            self.logger.info('天气数据处理和保存完成')
            return True
        return False
