import time
from datetime import datetime
from utils import log_info, log_error, log_warning


class TaskScheduler:
    def __init__(self, interval_minutes, task_callback):
        self.interval_minutes = interval_minutes
        self.task_callback = task_callback
        self.is_running = False
        self.execution_count = 0

    def execute_task(self):
        self.execution_count += 1
        log_info(f"========== 开始执行第 {self.execution_count} 次定时任务 ==========")
        start_time = datetime.now()

        try:
            self.task_callback()
        except Exception as e:
            log_error(f"定时任务执行异常: {str(e)}")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        log_info(f"第 {self.execution_count} 次任务执行完成，耗时: {duration:.2f} 秒")

    def start(self):
        if self.interval_minutes <= 0:
            log_error("时间间隔必须大于0分钟")
            return

        self.is_running = True
        log_info(f"定时任务调度器已启动，执行间隔: {self.interval_minutes} 分钟")

        self.execute_task()

        while self.is_running:
            try:
                seconds_remaining = self.interval_minutes * 60
                log_info(f"下次任务将在 {self.interval_minutes} 分钟后执行")

                while seconds_remaining > 0 and self.is_running:
                    time.sleep(min(1, seconds_remaining))
                    seconds_remaining -= 1

                if self.is_running:
                    self.execute_task()

            except KeyboardInterrupt:
                log_info("收到中断信号，正在停止定时任务...")
                self.stop()
            except Exception as e:
                log_error(f"调度器异常: {str(e)}")
                time.sleep(60)

    def stop(self):
        self.is_running = False
        log_info(f"定时任务调度器已停止，共执行 {self.execution_count} 次")

    def run_once(self):
        log_info("执行单次任务模式")
        self.execute_task()
