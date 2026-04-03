import yaml
import os
from utils import log_info, log_error, log_warning, CONFIG_DIR


class ConfigLoader:
    def __init__(self):
        self.config_path = os.path.join(CONFIG_DIR, "config.yaml")
        self.white_list_path = os.path.join(CONFIG_DIR, "city_white_list.yaml")
        self.config = None
        self.city_white_list = None
        self.valid_cities = []
        self.interval_minutes = 30

    def load_yaml_file(self, file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            log_error(f"配置文件不存在: {file_path}")
            return None
        except yaml.YAMLError as e:
            log_error(f"YAML解析错误 {file_path}: {str(e)}")
            return None
        except Exception as e:
            log_error(f"读取配置文件失败 {file_path}: {str(e)}")
            return None

    def load_city_white_list(self):
        log_info("正在加载城市白名单")
        white_list_data = self.load_yaml_file(self.white_list_path)
        if white_list_data and "cities" in white_list_data:
            self.city_white_list = white_list_data["cities"]
            log_info(f"白名单加载成功，共 {len(self.city_white_list)} 个城市")
            return True
        log_error("城市白名单加载失败或格式错误")
        return False

    def validate_config(self):
        if not self.config:
            log_error("配置文件为空")
            return False

        if "cities" not in self.config:
            log_error("配置文件缺少cities字段")
            return False

        configured_cities = self.config["cities"]
        if not isinstance(configured_cities, list):
            log_error("cities必须是列表类型")
            return False

        if len(configured_cities) < 1 or len(configured_cities) > 5:
            log_error(f"城市数量必须在1-5个之间，当前配置: {len(configured_cities)} 个")
            return False

        for city in configured_cities:
            if city in self.city_white_list:
                self.valid_cities.append(city)
            else:
                log_warning(f"城市 [{city}] 不在白名单中，已跳过")

        if len(self.valid_cities) == 0:
            log_error("没有有效的城市配置")
            return False

        log_info(f"有效配置城市: {', '.join(self.valid_cities)}")

        if "schedule" in self.config and "interval_minutes" in self.config["schedule"]:
            self.interval_minutes = self.config["schedule"]["interval_minutes"]
            if self.interval_minutes < 1:
                log_warning("时间间隔不能小于1分钟，已设置为1分钟")
                self.interval_minutes = 1

        log_info(f"定时任务间隔: {self.interval_minutes} 分钟")
        return True

    def load_and_validate(self):
        log_info("开始加载并校验配置文件")

        if not self.load_city_white_list():
            return False

        self.config = self.load_yaml_file(self.config_path)
        if not self.config:
            return False

        if not self.validate_config():
            return False

        log_info("配置文件校验通过")
        return True

    def get_valid_cities(self):
        return self.valid_cities

    def get_interval_minutes(self):
        return self.interval_minutes
