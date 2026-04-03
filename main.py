import sys
from utils import log_info, log_error
from config_loader import ConfigLoader
from weather_fetcher import WeatherFetcher
from data_saver import DataSaver
from task_scheduler import TaskScheduler


class WeatherApp:
    def __init__(self):
        self.config_loader = None
        self.weather_fetcher = None
        self.data_saver = None
        self.scheduler = None

    def initialize(self):
        log_info("=" * 50)
        log_info("天气定时获取程序启动中...")
        log_info("=" * 50)

        self.config_loader = ConfigLoader()
        if not self.config_loader.load_and_validate():
            log_error("配置校验失败，程序退出")
            return False

        self.weather_fetcher = WeatherFetcher()
        self.data_saver = DataSaver()

        log_info("程序初始化完成")
        return True

    def weather_task(self):
        cities = self.config_loader.get_valid_cities()
        weather_data_list = self.weather_fetcher.fetch_multiple_cities(cities)

        if weather_data_list:
            self.data_saver.save_and_report(weather_data_list)
        else:
            log_error("没有获取到有效的天气数据")

    def run(self):
        if not self.initialize():
            sys.exit(1)

        interval_minutes = self.config_loader.get_interval_minutes()

        self.scheduler = TaskScheduler(
            interval_minutes=interval_minutes,
            task_callback=self.weather_task
        )

        try:
            self.scheduler.start()
        except Exception as e:
            log_error(f"程序运行异常: {str(e)}")
            sys.exit(1)

    def run_once(self):
        if not self.initialize():
            sys.exit(1)

        log_info("运行单次任务模式")
        self.weather_task()
        log_info("单次任务执行完成")


def main():
    app = WeatherApp()

    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        app.run_once()
    else:
        app.run()


if __name__ == "__main__":
    main()
