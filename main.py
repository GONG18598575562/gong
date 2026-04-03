import signal
import sys
from typing import Optional
from config_loader import ConfigLoader, ConfigValidator
from weather_fetcher import WeatherFetcher
from data_saver import WeatherDataManager
from task_scheduler import TaskScheduler, TaskExecutor
from utils import LoggerManager


class WeatherApplication:
    
    def __init__(self):
        self.logger = LoggerManager.get_logger('WeatherApplication')
        self.config_loader = ConfigLoader()
        self.weather_fetcher: Optional[WeatherFetcher] = None
        self.data_manager: Optional[WeatherDataManager] = None
        self.task_scheduler: Optional[TaskScheduler] = None
        self.task_executor: Optional[TaskExecutor] = None
        self.config: Optional[dict] = None
    
    def initialize(self) -> bool:
        self.logger.info('=' * 50)
        self.logger.info('天气获取程序启动')
        self.logger.info('=' * 50)
        
        if not ConfigValidator.validate_all_paths():
            self.logger.error('目录结构校验失败')
            return False
        
        self.config = self.config_loader.load_app_config()
        if not self.config:
            self.logger.error('配置文件加载失败')
            return False
        
        api_config = self.config.get('api', {})
        self.weather_fetcher = WeatherFetcher(api_config)
        
        self.data_manager = WeatherDataManager()
        
        schedule_config = self.config.get('schedule', {})
        interval_minutes = schedule_config.get('interval_minutes', 60)
        self.task_scheduler = TaskScheduler(interval_minutes)
        
        self.task_executor = TaskExecutor()
        
        self.logger.info('程序初始化完成')
        return True
    
    def run(self) -> None:
        if not self.initialize():
            self.logger.error('程序初始化失败,退出')
            return
        
        cities = self.config.get('cities', [])
        if not cities:
            self.logger.error('未配置城市列表')
            return
        
        self._setup_signal_handlers()
        
        self.logger.info(f'开始定时获取天气,城市: {", ".join(cities)}')
        
        self.task_scheduler.start(
            self.task_executor.execute_weather_task,
            cities,
            self.weather_fetcher,
            self.data_manager
        )
        
        try:
            while self.task_scheduler.is_running():
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info('接收到中断信号')
            self.shutdown()
    
    def _setup_signal_handlers(self) -> None:
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame) -> None:
        self.logger.info(f'接收到信号 {signum}')
        self.shutdown()
        sys.exit(0)
    
    def shutdown(self) -> None:
        self.logger.info('正在关闭程序...')
        
        if self.task_scheduler:
            self.task_scheduler.stop()
        
        if self.task_executor:
            summary = self.task_executor.get_execution_summary()
            self.logger.info(f'执行摘要: {summary}')
        
        self.logger.info('=' * 50)
        self.logger.info('程序已关闭')
        self.logger.info('=' * 50)


def main():
    app = WeatherApplication()
    app.run()


if __name__ == '__main__':
    main()
