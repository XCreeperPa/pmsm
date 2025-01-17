import json
from pathlib import Path

class ConfigManager:
    def __init__(self, instance_dir):
        self.instance_dir = Path(instance_dir)
        self.config_path = self.instance_dir / "instance.json"

    def load_config(self):
        """加载实例配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        with open(self.config_path, "r") as f:
            return json.load(f)

    def save_config(self, config):
        """保存实例配置文件"""
        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=4)