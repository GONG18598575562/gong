import time
import threading
from datetime import datetime
from typing import Callable, Optional, Dict, Any
from utils import LoggerManager, get_current_timestamp


class TaskScheduler:
    
    def __init__(self, interval_minutes: float = 60.0):
        self.interval_minutes = interval_minutes
        self.interval_seconds = interval_minutes * 60
        self.logger = LoggerManager.get_logger('TaskScheduler')
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._task_count = 0
        self._stop_event = threading.Event()
    
    def set_interval(self, minutes: float) -> None:
        if minutes <= 0:
            self.logger.error('定时任务间隔必须大于0')
            return
        self.interval_minutes = minutes
        self.interval_seconds = minutes * 60
        self.logger.info(f'定时任务间隔设置为 {minutes} 分钟')
    
    def start(self, task_func: Callable, *args, **kwargs) -> bool:
        if self._running:
            self.logger.warning('定时任务已在运行中')
            return False
        
        self._running = True
        self._stop_event.clear()
        
        self._thread = threading.Thread(
            target=self._run_scheduler,
            args=(task_func, args, kwargs),
            daemon=True
        )
        self._thread.start()
        
        self.logger.info(f'定时任务启动,间隔 {self.interval_minutes} 分钟')
        return True
    
    def stop(self) -> None:
        if not self._running:
            self.logger.warning('定时任务未在运行')
            return
        
        self._running = False
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        self.logger.info('定时任务已停止')
    
    def _run_scheduler(self, task_func: Callable, args: tuple, kwargs: dict) -> None:
        self._execute_task(task_func, args, kwargs)
        
        while self._running and not self._stop_event.is_set():
            if self._stop_event.wait(timeout=self.interval_seconds):
                break
            
            if self._running:
                self._execute_task(task_func, args, kwargs)
    
    def _execute_task(self, task_func: Callable, args: tuple, kwargs: dict) -> None:
        self._task_count += 1
        task_id = self._task_count
        
        self.logger.info(f'开始执行第 {task_id} 次定时任务')
        start_time = datetime.now()
        
        try:
            task_func(*args, **kwargs)
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.logger.info(f'第 {task_id} 次定时任务执行完成,耗时 {duration:.2f} 秒')
        except Exception as e:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            self.logger.error(f'第 {task_id} 次定时任务执行失败,耗时 {duration:.2f} 秒,错误: {str(e)}')
    
    def is_running(self) -> bool:
        return self._running
    
    def get_task_count(self) -> int:
        return self._task_count


class TaskExecutor:
    
    def __init__(self):
        self.logger = LoggerManager.get_logger('TaskExecutor')
        self.execution_history: list = []
    
    def execute_weather_task(self, cities: list, weather_fetcher, data_manager) -> bool:
        self.logger.info(f'开始执行天气获取任务,城市: {", ".join(cities)}')
        
        weather_list = []
        success_count = 0
        fail_count = 0
        
        for city in cities:
            try:
                weather_data = weather_fetcher.fetch_weather(city)
                
                if weather_data:
                    from weather_fetcher import DataCleaner
                    cleaned_data = DataCleaner.clean_weather_data(weather_data)
                    
                    if cleaned_data:
                        weather_list.append(cleaned_data)
                        success_count += 1
                    else:
                        fail_count += 1
                        self.logger.warning(f'{city} 天气数据清洗失败')
                else:
                    fail_count += 1
                    self.logger.warning(f'{city} 天气数据获取失败')
                    
            except Exception as e:
                fail_count += 1
                self.logger.error(f'{city} 天气任务执行异常: {str(e)}')
        
        if weather_list:
            data_manager.process_and_save(weather_list)
        
        execution_record = {
            'timestamp': get_current_timestamp(),
            'total_cities': len(cities),
            'success_count': success_count,
            'fail_count': fail_count
        }
        self.execution_history.append(execution_record)
        
        self.logger.info(f'天气任务执行完成,成功: {success_count},失败: {fail_count}')
        return success_count > 0
    
    def get_execution_summary(self) -> Dict[str, Any]:
        if not self.execution_history:
            return {'total_executions': 0}
        
        total_success = sum(e['success_count'] for e in self.execution_history)
        total_fail = sum(e['fail_count'] for e in self.execution_history)
        
        return {
            'total_executions': len(self.execution_history),
            'total_success': total_success,
            'total_fail': total_fail,
            'last_execution': self.execution_history[-1] if self.execution_history else None
        }
