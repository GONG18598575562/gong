"""
天气数据采集程序 - 主入口
定时获取指定城市天气数据，自动格式化处理、本地持久化存储、生成天气报告
"""

import sys
import io
import signal
import time
from typing import Optional

# 设置UTF-8编码（Windows兼容）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from utils import LoggerManager, ExceptionHandler, PathValidator
from config_loader import ConfigManager, ConfigLoader
from weather_fetcher import WeatherDataProcessor
from data_saver import DataSaver
from task_scheduler import TaskScheduler, TaskExecutor, SingleTaskRunner, SchedulerManager


class WeatherApplication:
    """天气应用主类 - 整合所有模块功能"""

    def __init__(self):
        self.logger_manager: Optional[LoggerManager] = None
        self.logger = None
        self.config_manager: Optional[ConfigManager] = None
        self.config_loader: Optional[ConfigLoader] = None
        self.weather_processor: Optional[WeatherDataProcessor] = None
        self.data_saver: Optional[DataSaver] = None
        self.scheduler: Optional[TaskScheduler] = None
        self.task_executor: Optional[TaskExecutor] = None
        self._running = False

    def initialize(self) -> bool:
        """初始化应用程序"""
        try:
            print("=" * 60)
            print("天气数据采集程序 - 初始化中...")
            print("=" * 60)

            # 1. 校验目录结构
            print("\n[1/5] 校验目录结构...")
            if not self._validate_directories():
                print("目录结构校验失败")
                return False
            print("[OK] 目录结构校验通过")

            # 2. 初始化配置管理器
            print("\n[2/5] 加载配置文件...")
            self.config_manager = ConfigManager()
            if not self.config_manager.initialize():
                print("配置初始化失败")
                return False
            self.config_loader = self.config_manager.get_config_loader()
            print("[OK] 配置文件加载成功")

            # 3. 初始化日志管理器
            print("\n[3/5] 初始化日志系统...")
            log_config = self.config_loader.get_logging_config()
            self.logger_manager = LoggerManager(
                level=log_config.get('level', 'INFO')
            )
            self.logger = self.logger_manager.get_logger('WeatherApplication')
            self.logger.info("日志系统初始化完成")
            print("[OK] 日志系统初始化成功")

            # 4. 初始化天气数据处理器
            print("\n[4/5] 初始化天气数据处理器...")
            api_config = self.config_loader.get_weather_api_config()
            self.weather_processor = WeatherDataProcessor(api_config)
            self.logger.info("天气数据处理器初始化完成")
            print("[OK] 天气数据处理器初始化成功")

            # 5. 初始化数据存储器
            print("\n[5/5] 初始化数据存储器...")
            storage_config = self.config_loader.get_storage_config()
            self.data_saver = DataSaver(storage_config)
            self.logger.info("数据存储器初始化完成")
            print("[OK] 数据存储器初始化成功")

            # 初始化任务执行器
            self.task_executor = TaskExecutor(
                self.config_loader,
                self.weather_processor,
                self.data_saver
            )

            print("\n" + "=" * 60)
            print("初始化完成！")
            print("=" * 60)

            self._show_config_summary()

            return True

        except Exception as e:
            error_msg = ExceptionHandler.handle_exception(e, None, "应用程序初始化失败")
            print(f"\n初始化失败: {error_msg}")
            return False

    def _validate_directories(self) -> bool:
        """校验并创建必要的目录结构"""
        try:
            directories = [
                './config/',
                './weather/data/',
                './weather/logs/',
                './weather/report/'
            ]

            for dir_path in directories:
                PathValidator.ensure_directory_exists(dir_path)

            return True

        except Exception as e:
            print(f"目录校验失败: {str(e)}")
            return False

    def _show_config_summary(self) -> None:
        """显示配置摘要"""
        if not self.config_loader:
            return

        print("\n配置摘要:")
        print(f"  - 定时间隔: {self.config_loader.get_schedule_interval()} 分钟")
        print(f"  - 目标城市: {', '.join(self.config_loader.get_target_cities())}")
        print(f"  - 日志级别: {self.config_loader.get_logging_config().get('level', 'INFO')}")
        print(f"  - 数据保留: {self.config_loader.get_storage_config().get('data_retention_days', 30)} 天")
        print(f"  - 报告保留: {self.config_loader.get_storage_config().get('report_retention_days', 7)} 天")
        print()

    def run_once(self) -> dict:
        """执行单次天气数据采集任务"""
        if not self.task_executor:
            raise RuntimeError("应用程序未初始化")

        self.logger.info("执行单次任务模式")
        return self.task_executor.execute_weather_task()

    def start_scheduler(self) -> bool:
        """启动定时任务调度器"""
        if not self.config_loader or not self.task_executor:
            raise RuntimeError("应用程序未初始化")

        try:
            interval = self.config_loader.get_schedule_interval()

            # 创建调度器
            self.scheduler = TaskScheduler(interval)
            self.scheduler.set_task(self.task_executor.execute_weather_task)

            # 设置信号处理
            self._setup_signal_handlers()

            # 启动调度器
            if self.scheduler.start():
                self._running = True
                self.logger.info("定时任务调度器已启动")
                return True
            else:
                self.logger.error("定时任务调度器启动失败")
                return False

        except Exception as e:
            ExceptionHandler.handle_exception(e, self.logger, "启动调度器失败")
            return False

    def stop_scheduler(self) -> None:
        """停止定时任务调度器"""
        if self.scheduler and self.scheduler.is_running():
            self.scheduler.stop()
            self._running = False
            self.logger.info("定时任务调度器已停止")

    def _setup_signal_handlers(self) -> None:
        """设置信号处理器"""
        def signal_handler(signum, frame):
            self.logger.info(f"接收到信号 {signum}，正在停止程序...")
            self.stop_scheduler()
            sys.exit(0)

        # 注册信号处理器
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, signal_handler)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, signal_handler)

    def run_forever(self) -> None:
        """持续运行定时任务"""
        if not self.start_scheduler():
            return

        print("\n定时任务已启动，按 Ctrl+C 停止程序\n")

        try:
            while self._running and self.scheduler and self.scheduler.is_running():
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n接收到中断信号，正在停止...")
        finally:
            self.stop_scheduler()

    def get_status(self) -> dict:
        """获取应用程序状态"""
        status = {
            'initialized': self.config_loader is not None,
            'running': self._running,
            'scheduler_status': None
        }

        if self.scheduler:
            status['scheduler_status'] = self.scheduler.get_status()

        return status


def print_usage() -> None:
    """打印使用说明"""
    print("""
天气数据采集程序 - 使用说明

用法:
    python main.py [模式]

模式:
    once    - 执行单次任务（默认）
    daemon  - 启动定时任务守护进程

示例:
    python main.py           # 执行单次任务
    python main.py once      # 执行单次任务
    python main.py daemon    # 启动定时任务

配置文件:
    ./config/config.yaml          - 用户配置（可修改）
    ./config/city_white_list.yaml - 城市白名单（只读）

输出目录:
    ./weather/data/   - 天气数据文件（JSON格式）
    ./weather/logs/   - 日志文件（LOG格式）
    ./weather/report/ - 报告文件（Markdown格式）
""")


def main():
    """主函数"""
    # 解析命令行参数
    mode = 'once'
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ('-h', '--help', 'help'):
            print_usage()
            sys.exit(0)
        elif arg in ('once', 'daemon'):
            mode = arg
        else:
            print(f"未知参数: {arg}")
            print_usage()
            sys.exit(1)

    # 创建应用程序实例
    app = WeatherApplication()

    # 初始化应用程序
    if not app.initialize():
        print("\n应用程序初始化失败，请检查配置文件和目录结构")
        sys.exit(1)

    # 根据模式执行
    if mode == 'once':
        print("\n执行单次天气数据采集任务...\n")
        result = app.run_once()

        print("\n" + "=" * 60)
        print("任务执行结果:")
        print("=" * 60)
        print(f"成功: {result['success']}")
        print(f"城市总数: {result['cities_total']}")
        print(f"成功城市: {result['cities_success']}")
        print(f"失败城市: {result['cities_failed']}")

        if result['data_files']:
            print(f"\n数据文件 ({len(result['data_files'])} 个):")
            for filepath in result['data_files']:
                print(f"  - {filepath}")

        if result['report_file']:
            print(f"\n报告文件: {result['report_file']}")

        if result['errors']:
            print(f"\n错误信息:")
            for error in result['errors']:
                print(f"  - {error}")

        print("=" * 60)

        # 根据结果设置退出码
        sys.exit(0 if result['success'] else 1)

    elif mode == 'daemon':
        app.run_forever()


if __name__ == '__main__':
    main()
