import json
import os
from datetime import datetime
from utils import (
    log_info,
    log_error,
    get_date_string,
    get_datetime_string,
    WEATHER_DATA_DIR,
    WEATHER_REPORT_DIR,
    ensure_directories
)


class DataSaver:
    def __init__(self):
        ensure_directories()

    def save_weather_data(self, weather_data_list):
        if not weather_data_list:
            log_error("没有天气数据需要保存")
            return False

        try:
            datetime_str = get_datetime_string()
            file_name = f"weather_{datetime_str}.json"
            file_path = os.path.join(WEATHER_DATA_DIR, file_name)

            output_data = {
                "generate_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_count": len(weather_data_list),
                "weather_data": weather_data_list
            }

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2)

            log_info(f"天气数据已保存到: {file_path}")
            return True
        except Exception as e:
            log_error(f"保存天气数据失败: {str(e)}")
            return False

    def generate_daily_report(self, weather_data_list):
        if not weather_data_list:
            log_error("没有天气数据，无法生成报告")
            return False

        try:
            date_str = get_date_string()
            file_name = f"weather_report_{date_str}.md"
            file_path = os.path.join(WEATHER_REPORT_DIR, file_name)

            report_content = self._build_report_content(weather_data_list)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(report_content)

            log_info(f"天气报告已生成: {file_path}")
            return True
        except Exception as e:
            log_error(f"生成天气报告失败: {str(e)}")
            return False

    def _build_report_content(self, weather_data_list):
        generate_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        avg_temp = sum(d["temperature"] for d in weather_data_list) / len(weather_data_list)
        max_temp = max(d["temperature"] for d in weather_data_list)
        min_temp = min(d["temperature"] for d in weather_data_list)
        avg_humidity = sum(d["humidity"] for d in weather_data_list) / len(weather_data_list)

        content = f"""# 每日天气汇总报告

**生成时间**: {generate_time}
**覆盖城市**: {len(weather_data_list)} 个

## 统计摘要

| 统计项 | 值 |
|--------|----|
| 平均温度 | {avg_temp:.1f}°C |
| 最高温度 | {max_temp:.1f}°C |
| 最低温度 | {min_temp:.1f}°C |
| 平均湿度 | {avg_humidity:.1f}% |

## 各城市天气详情

"""
        for data in weather_data_list:
            content += f"""### {data['city']}

- **天气状况**: {data['weather_condition']}
- **温度**: {data['temperature']}°C
- **湿度**: {data['humidity']}%
- **风力**: {data['wind_power']}
- **更新时间**: {data['update_time']}

"""

        content += """
---
*本报告由天气定时获取程序自动生成*
"""
        return content

    def save_and_report(self, weather_data_list):
        log_info("开始保存数据并生成报告")

        save_success = self.save_weather_data(weather_data_list)
        report_success = self.generate_daily_report(weather_data_list)

        if save_success and report_success:
            log_info("数据保存和报告生成均成功")
            return True
        else:
            log_error("数据保存或报告生成失败")
            return False
