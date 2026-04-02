"""
定时任务模块
实现定时任务逻辑，管理任务执行周期
"""

import time
import threading
from typing import Callable, Optional, Any
from datetime import datetime

from utils import LoggerManager, ExceptionHandler, DateTimeUtil


class TaskScheduler:
    """任务调度器 - 管理定时任务执行"""

    def __init__(self, interval_minutes: int = 30):
        self.logger_manager = LoggerManager()
        self.logger = self.logger_manager.get_logger('TaskScheduler')
        self.interval_minutes = max(1, min(interval_minutes, 1440))  # 限制1-1440分钟
        self.interval_seconds = self.interval_minutes * 60
        self._running = False
        self._task_func: Optional[Callable[..., Any]] = None
        self._task_args: tuple = ()
        self._task_kwargs: dict = {}
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._execution_count = 0
        self._last_execution_time: Optional[datetime] = None

    def set_task(
        self,
        task_func: Callable[..., Any],
        *args,
        **kwargs
    ) -> None:
        """设置要执行的任务"""
        self._task_func = task_func
        self._task_args = args
        self._task_kwargs = kwargs
        self.logger.info(f"任务已设置: {task_func.__name__}")

    def start(self) -> bool:
        """启动定时任务调度器"""
        if self._running:
            self.logger.warning("调度器已在运行中")
            return False

        if self._task_func is None:
            self.logger.error("未设置任务函数，无法启动")
            return False

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._thread.start()

        self.logger.info(f"定时任务调度器已启动，执行间隔: {self.interval_minutes} 分钟")
        return True

    def stop(self) -> None:
        """停止定时任务调度器"""
        if not self._running:
            self.logger.warning("调度器未在运行")
            return

        self.logger.info("正在停止定时任务调度器...")
        self._running = False
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

        self.logger.info("定时任务调度器已停止")

    def _run_scheduler(self) -> None:
        """调度器主循环"""
        self.logger.info("调度器主循环开始")

        # 首次立即执行一次
        self._execute_task()

        while self._running and not self._stop_event.is_set():
            # 等待指定间隔
            wait_start = time.time()
            while (time.time() - wait_start) < self.interval_seconds:
                if self._stop_event.is_set():
                    break
                time.sleep(1)

            if not self._running or self._stop_event.is_set():
                break

            # 执行定时任务
            self._execute_task()

        self.logger.info("调度器主循环结束")

    def _execute_task(self) -> None:
        """执行任务"""
        try:
            self._execution_count += 1
            self._last_execution_time = datetime.now()

            self.logger.info(f"开始执行第 {self._execution_count} 次定时任务")
            self.logger.info(f"执行时间: {DateTimeUtil.get_current_timestamp()}")

            if self._task_func:
                self._task_func(*self._task_args, **self._task_kwargs)

            self.logger.info(f"第 {self._execution_count} 次定时任务执行完成")

        except Exception as e:
            ExceptionHandler.handle_exception(
                e, self.logger, f"第 {self._execution_count} 次定时任务执行失败"
            )

    def is_running(self) -> bool:
        """检查调度器是否正在运行"""
        return self._running

    def get_status(self) -> dict:
        """获取调度器状态"""
        return {
            'running': self._running,
            'interval_minutes': self.interval_minutes,
            'execution_count': self._execution_count,
            'last_execution_time': (
                DateTimeUtil.format_datetime(self._last_execution_time)
                if self._last_execution_time else None
            ),
            'task_name': self._task_func.__name__ if self._task_func else None
        }

    def update_interval(self, new_interval_minutes: int) -> bool:
        """更新执行间隔（需要重启调度器生效）"""
        try:
            new_interval = max(1, min(new_interval_minutes, 1440))
            if new_interval != self.interval_minutes:
                self.interval_minutes = new_interval
                self.interval_seconds = new_interval * 60
                self.logger.info(f"执行间隔已更新为: {self.interval_minutes} 分钟")
                return True
            return False
        except Exception as e:
            ExceptionHandler.handle_exception(e, self.logger, "更新执行间隔失败")
            return False


class TaskExecutor:
    """任务执行器 - 封装天气数据采集任务"""

    def __init__(
        self,
        config_loader,
        weather_processor,
        data_saver
    ):
        self.logger_manager = LoggerManager()
        self.logger = self.logger_manager.get_logger('TaskExecutor')
        self.config_loader = config_loader
        self.weather_processor = weather_processor
        self.data_saver = data_saver

    def execute_weather_task(self) -> dict:
        """执行天气数据采集任务"""
        result = {
            'success': False,
            'cities_total': 0,
            'cities_success': 0,
            'cities_failed': 0,
            'data_files': [],
            'report_file': None,
            'errors': []
        }

        try:
            self.logger.info("=" * 50)
            self.logger.info("开始执行天气数据采集任务")
            self.logger.info("=" * 50)

            # 1. 获取目标城市列表
            cities = self.config_loader.get_target_cities()
            result['cities_total'] = len(cities)
            self.logger.info(f"目标城市: {cities}")

            if not cities:
                error_msg = "没有配置目标城市"
                self.logger.error(error_msg)
                result['errors'].append(error_msg)
                return result

            # 2. 清理过期文件
            self.logger.info("清理过期文件...")
            self.data_saver.clean_old_files()
            self.logger_manager.clean_old_logs(
                self.config_loader.get_logging_config().get('max_log_files', 7)
            )

            # 3. 批量获取天气数据
            self.logger.info("开始获取天气数据...")
            weather_data_list = self.weather_processor.fetch_multiple_cities(cities)

            # 4. 过滤无效数据
            valid_data_list = self.weather_processor.filter_invalid_data(weather_data_list)
            result['cities_success'] = len(valid_data_list)
            result['cities_failed'] = len(cities) - len(valid_data_list)

            if not valid_data_list:
                error_msg = "没有获取到有效的天气数据"
                self.logger.error(error_msg)
                result['errors'].append(error_msg)
                return result

            # 5. 保存天气数据
            self.logger.info("保存天气数据...")
            saved_files = self.data_saver.save_batch_weather_data(valid_data_list)
            result['data_files'] = saved_files

            # 6. 生成每日报告
            self.logger.info("生成天气报告...")
            report_file = self.data_saver.generate_daily_report(valid_data_list)
            result['report_file'] = report_file

            result['success'] = True

            self.logger.info("=" * 50)
            self.logger.info("天气数据采集任务执行完成")
            self.logger.info(f"成功: {result['cities_success']}/{result['cities_total']} 个城市")
            self.logger.info("=" * 50)

        except Exception as e:
            error_msg = ExceptionHandler.handle_exception(
                e, self.logger, "天气数据采集任务执行异常"
            )
            result['errors'].append(error_msg)

        return result


class SingleTaskRunner:
    """单次任务运行器 - 用于非定时执行"""

    def __init__(
        self,
        config_loader,
        weather_processor,
        data_saver
    ):
        self.logger_manager = LoggerManager()
        self.logger = self.logger_manager.get_logger('SingleTaskRunner')
        self.executor = TaskExecutor(config_loader, weather_processor, data_saver)

    def run_once(self) -> dict:
        """执行单次任务"""
        self.logger.info("执行单次天气数据采集任务")
        return self.executor.execute_weather_task()


class SchedulerManager:
    """调度器管理器 - 管理多个调度器实例"""

    _schedulers: dict = {}

    @classmethod
    def create_scheduler(
        cls,
        name: str,
        interval_minutes: int
    ) -> TaskScheduler:
        """创建新的调度器"""
        if name in cls._schedulers:
            raise ValueError(f"调度器 '{name}' 已存在")

        scheduler = TaskScheduler(interval_minutes)
        cls._schedulers[name] = scheduler
        return scheduler

    @classmethod
    def get_scheduler(cls, name: str) -> Optional[TaskScheduler]:
        """获取调度器"""
        return cls._schedulers.get(name)

    @classmethod
    def stop_all(cls) -> None:
        """停止所有调度器"""
        for name, scheduler in cls._schedulers.items():
            try:
                scheduler.stop()
            except Exception as e:
                print(f"停止调度器 '{name}' 失败: {str(e)}")

        cls._schedulers.clear()

    @classmethod
    def get_all_status(cls) -> dict:
        """获取所有调度器状态"""
        return {
            name: scheduler.get_status()
            for name, scheduler in cls._schedulers.items()
        }
