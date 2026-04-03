import os
import logging
from datetime import datetime
from pathlib import Path

CONFIG_DIR = "./config/"
WEATHER_DATA_DIR = "./weather/data/"
WEATHER_LOGS_DIR = "./weather/logs/"
WEATHER_REPORT_DIR = "./weather/report/"


def ensure_directories():
    directories = [
        CONFIG_DIR,
        WEATHER_DATA_DIR,
        WEATHER_LOGS_DIR,
        WEATHER_REPORT_DIR
    ]
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def setup_logger():
    ensure_directories()
    today_str = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(WEATHER_LOGS_DIR, f"task_log_{today_str}.log")
    
    logger = logging.getLogger("weather_task")
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        return logger
    
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger


logger = setup_logger()


def log_info(message):
    logger.info(message)


def log_error(message):
    logger.error(message)


def log_warning(message):
    logger.warning(message)


def get_current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_date_string():
    return datetime.now().strftime("%Y%m%d")


def get_datetime_string():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def validate_path(path, expected_prefix=None):
    if expected_prefix and not path.startswith(expected_prefix):
        return False
    try:
        Path(path)
        return True
    except Exception:
        return False


def handle_exception(exception, context=""):
    error_msg = f"{context} - 异常: {str(exception)}" if context else f"异常: {str(exception)}"
    log_error(error_msg)
    return False


def is_valid_temperature(temp):
    if temp is None:
        return False
    try:
        temp_float = float(temp)
        return -50 <= temp_float <= 60
    except (ValueError, TypeError):
        return False


def is_valid_humidity(humidity):
    if humidity is None:
        return False
    try:
        humidity_float = float(humidity)
        return 0 <= humidity_float <= 100
    except (ValueError, TypeError):
        return False


def clean_string(input_str):
    if input_str is None:
        return ""
    return str(input_str).strip().replace("\n", "").replace("\r", "")
