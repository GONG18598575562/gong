"""
数据存储模块
格式化存储天气数据，生成markdown报告
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from utils import (
    LoggerManager,
    ExceptionHandler,
    PathValidator,
    FileNameGenerator,
    DateTimeUtil
)


class DataSaver:
    """数据存储器 - 保存天气数据和生成报告"""

    DATA_DIR = './weather/data/'
    REPORT_DIR = './weather/report/'

    def __init__(self, storage_config: Optional[Dict[str, Any]] = None):
        self.logger_manager = LoggerManager()
        self.logger = self.logger_manager.get_logger('DataSaver')
        self.storage_config = storage_config or {}
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """确保数据目录存在"""
        PathValidator.ensure_directory_exists(self.DATA_DIR)
        PathValidator.ensure_directory_exists(self.REPORT_DIR)

    def save_weather_data(self, weather_data: Dict[str, Any]) -> Optional[str]:
        """保存单条天气数据到JSON文件"""
        try:
            city = weather_data.get('city')
            if not city:
                self.logger.error("天气数据缺少城市信息")
                return None

            filename = FileNameGenerator.generate_weather_filename(city)
            filepath = os.path.join(self.DATA_DIR, filename)

            # 准备要保存的数据（移除原始数据以减小文件大小）
            data_to_save = {k: v for k, v in weather_data.items() if k != 'raw_data'}

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)

            self.logger.info(f"天气数据已保存: {filepath}")
            return filepath

        except Exception as e:
            ExceptionHandler.handle_exception(e, self.logger, "保存天气数据失败")
            return None

    def save_batch_weather_data(self, weather_data_list: List[Dict[str, Any]]) -> List[str]:
        """批量保存天气数据"""
        saved_files = []

        for data in weather_data_list:
            try:
                filepath = self.save_weather_data(data)
                if filepath:
                    saved_files.append(filepath)
            except Exception as e:
                city = data.get('city', '未知')
                ExceptionHandler.handle_exception(
                    e, self.logger, f"保存城市 '{city}' 数据失败"
                )
                continue

        self.logger.info(f"批量保存完成: {len(saved_files)}/{len(weather_data_list)} 条数据")
        return saved_files

    def generate_daily_report(self, weather_data_list: List[Dict[str, Any]]) -> Optional[str]:
        """生成每日天气汇总报告（Markdown格式）"""
        try:
            if not weather_data_list:
                self.logger.warning("没有天气数据，无法生成报告")
                return None

            report_date = DateTimeUtil.get_current_date()
            filename = FileNameGenerator.generate_report_filename()
            filepath = os.path.join(self.REPORT_DIR, filename)

            # 生成报告内容
            report_content = self._build_report_content(weather_data_list, report_date)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(report_content)

            self.logger.info(f"天气报告已生成: {filepath}")
            return filepath

        except Exception as e:
            ExceptionHandler.handle_exception(e, self.logger, "生成天气报告失败")
            return None

    def _build_report_content(self, weather_data_list: List[Dict[str, Any]], report_date: str) -> str:
        """构建报告内容"""
        lines = []

        # 报告标题
        lines.append(f"# 每日天气汇总报告")
        lines.append("")
        lines.append(f"**报告日期**: {report_date}")
        lines.append(f"**生成时间**: {DateTimeUtil.get_current_timestamp()}")
        lines.append(f"**数据来源**: wttr.in 公开天气API")
        lines.append("")

        # 概览统计
        lines.append("## 概览")
        lines.append("")
        lines.append(f"- 监测城市数: {len(weather_data_list)}")

        # 计算平均温度
        temps = []
        for data in weather_data_list:
            try:
                temp = float(data.get('temperature', 0))
                temps.append(temp)
            except (ValueError, TypeError):
                continue

        if temps:
            avg_temp = sum(temps) / len(temps)
            lines.append(f"- 平均温度: {avg_temp:.1f}°C")
            lines.append(f"- 最高温度: {max(temps):.1f}°C")
            lines.append(f"- 最低温度: {min(temps):.1f}°C")

        lines.append("")

        # 详细数据表格
        lines.append("## 各城市天气详情")
        lines.append("")
        lines.append("| 城市 | 温度(°C) | 湿度(%) | 天气状况 | 风力 | 更新时间 |")
        lines.append("|------|----------|---------|----------|------|----------|")

        for data in weather_data_list:
            city = data.get('city', '未知')
            temp = data.get('temperature', 'N/A')
            humidity = data.get('humidity', 'N/A')
            condition = data.get('condition', '未知')
            wind = data.get('wind', '未知')
            update_time = data.get('update_time', '未知')

            lines.append(f"| {city} | {temp} | {humidity} | {condition} | {wind} | {update_time} |")

        lines.append("")

        # 温度分布
        if len(weather_data_list) > 1:
            lines.append("## 温度分布")
            lines.append("")

            # 按温度排序
            sorted_data = sorted(
                weather_data_list,
                key=lambda x: float(x.get('temperature', 0)) if x.get('temperature') else 0,
                reverse=True
            )

            lines.append("### 温度排行（从高到低）")
            lines.append("")
            for i, data in enumerate(sorted_data, 1):
                city = data.get('city', '未知')
                temp = data.get('temperature', 'N/A')
                condition = data.get('condition', '未知')
                lines.append(f"{i}. **{city}**: {temp}°C ({condition})")

            lines.append("")

        # 天气状况统计
        lines.append("## 天气状况统计")
        lines.append("")

        condition_count = {}
        for data in weather_data_list:
            condition = data.get('condition', '未知')
            condition_count[condition] = condition_count.get(condition, 0) + 1

        for condition, count in sorted(condition_count.items(), key=lambda x: x[1], reverse=True):
            lines.append(f"- {condition}: {count} 个城市")

        lines.append("")

        # 数据文件索引
        lines.append("## 数据文件索引")
        lines.append("")
        lines.append("本次采集的原始数据文件：")
        lines.append("")

        for data in weather_data_list:
            city = data.get('city', '未知')
            filename = FileNameGenerator.generate_weather_filename(city)
            lines.append(f"- {city}: `{filename}`")

        lines.append("")

        # 页脚
        lines.append("---")
        lines.append("")
        lines.append(f"*报告由天气数据采集程序自动生成*")
        lines.append(f"*生成时间: {DateTimeUtil.get_current_timestamp()}*")

        return "\n".join(lines)

    def clean_old_files(self) -> None:
        """清理过期的数据文件和报告文件"""
        try:
            data_retention = self.storage_config.get('data_retention_days', 30)
            report_retention = self.storage_config.get('report_retention_days', 7)

            self._clean_directory(self.DATA_DIR, data_retention, 'weather_*.json')
            self._clean_directory(self.REPORT_DIR, report_retention, 'weather_report_*.md')

        except Exception as e:
            ExceptionHandler.handle_exception(e, self.logger, "清理过期文件失败")

    def _clean_directory(self, directory: str, retention_days: int, pattern: str) -> None:
        """清理指定目录的过期文件"""
        try:
            current_time = datetime.now()
            dir_path = Path(directory)

            if not dir_path.exists():
                return

            for file_path in dir_path.glob(pattern):
                try:
                    file_stat = file_path.stat()
                    file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
                    days_diff = (current_time - file_mtime).days

                    if days_diff > retention_days:
                        file_path.unlink()
                        self.logger.info(f"已删除过期文件: {file_path.name}")
                except Exception as e:
                    self.logger.error(f"删除文件失败 {file_path.name}: {str(e)}")

        except Exception as e:
            self.logger.error(f"清理目录失败 {directory}: {str(e)}")


class ReportGenerator:
    """报告生成器 - 生成各类天气报告"""

    def __init__(self):
        self.logger_manager = LoggerManager()
        self.logger = self.logger_manager.get_logger('ReportGenerator')

    def generate_city_comparison_report(
        self,
        weather_data_list: List[Dict[str, Any]],
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """生成城市对比报告"""
        try:
            if not weather_data_list:
                return None

            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = f"./weather/report/city_comparison_{timestamp}.md"

            lines = []
            lines.append("# 城市天气对比报告")
            lines.append("")
            lines.append(f"**生成时间**: {DateTimeUtil.get_current_timestamp()}")
            lines.append("")

            # 对比表格
            lines.append("## 数据对比")
            lines.append("")
            lines.append("| 城市 | 温度 | 湿度 | 天气 | 舒适度 |")
            lines.append("|------|------|------|------|--------|")

            for data in weather_data_list:
                city = data.get('city', '未知')
                temp = data.get('temperature', 'N/A')
                humidity = data.get('humidity', 'N/A')
                condition = data.get('condition', '未知')
                comfort = self._calculate_comfort_level(data)

                lines.append(f"| {city} | {temp}°C | {humidity}% | {condition} | {comfort} |")

            lines.append("")

            # 舒适度分析
            lines.append("## 舒适度分析")
            lines.append("")

            for data in weather_data_list:
                city = data.get('city', '未知')
                comfort = self._calculate_comfort_level(data)
                suggestion = self._get_weather_suggestion(data)

                lines.append(f"### {city}")
                lines.append(f"- 舒适度: {comfort}")
                lines.append(f"- 建议: {suggestion}")
                lines.append("")

            content = "\n".join(lines)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.logger.info(f"城市对比报告已生成: {output_path}")
            return output_path

        except Exception as e:
            ExceptionHandler.handle_exception(e, self.logger, "生成对比报告失败")
            return None

    def _calculate_comfort_level(self, data: Dict[str, Any]) -> str:
        """计算舒适度等级"""
        try:
            temp = float(data.get('temperature', 20))
            humidity = float(data.get('humidity', 50))

            # 简单舒适度计算
            if 18 <= temp <= 26 and 40 <= humidity <= 70:
                return "舒适"
            elif temp < 10 or temp > 35:
                return "不舒适"
            elif humidity > 80:
                return "潮湿"
            elif humidity < 30:
                return "干燥"
            else:
                return "一般"

        except (ValueError, TypeError):
            return "未知"

    def _get_weather_suggestion(self, data: Dict[str, Any]) -> str:
        """获取天气建议"""
        try:
            temp = float(data.get('temperature', 20))
            condition = data.get('condition', '')

            suggestions = []

            if temp < 5:
                suggestions.append("注意保暖，建议穿厚外套")
            elif temp < 15:
                suggestions.append("天气较凉，建议穿长袖")
            elif temp > 30:
                suggestions.append("天气炎热，注意防暑降温")

            if '雨' in condition:
                suggestions.append("有雨，出门请带伞")
            elif '雪' in condition:
                suggestions.append("有雪，注意防滑")
            elif '雾' in condition or '霾' in condition:
                suggestions.append("能见度低，注意交通安全")

            if not suggestions:
                suggestions.append("天气适宜，适合户外活动")

            return "; ".join(suggestions)

        except (ValueError, TypeError):
            return "暂无建议"
