import subprocess
import json
from pathlib import Path
import time
import os
from pmsm.config_manager import ConfigManager
import threading
from pmsm.log_manager import LogManager
from datetime import datetime

log_manager = LogManager()

class InstanceManager:
    def __init__(self, instances_dir="instances"):
        # 将 instances_dir 转换为绝对路径
        self.instances_dir = Path(instances_dir).resolve()
        print("Instances directory:", self.instances_dir)  # 打印实例目录路径
        if not self.instances_dir.exists():
            raise FileNotFoundError(f"Instances directory not found: {self.instances_dir}")

    def start_instance(self, instance_name):
        """启动指定实例"""
        instance_dir = self.instances_dir / instance_name
        print("Instance directory:", instance_dir)  # 打印实例目录路径
        if not instance_dir.exists():
            raise FileNotFoundError(f"Instance directory not found: {instance_dir}")

        # 加载配置
        config_manager = ConfigManager(instance_dir)
        config = config_manager.load_config()

        # 获取 JDK 和服务器 JAR 路径
        java_path = str((instance_dir / config["jdk_path"]).resolve())
        server_jar = str((instance_dir / config["server_jar"]).resolve())

        # 启动服务器进程
        process = subprocess.Popen(
            [java_path, "-jar", server_jar, "nogui"],
            cwd=instance_dir / "server",
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        try:
            # 创建新的日志表并记录启动日志
            start_id = log_manager.new_instance_start(instance_name)
            print(f"Created new log table with start_id: {start_id}")

            # 保存进程状态到数据库
            log_manager.update_instance_state(instance_name, {
                "pid": process.pid,
                "start_id": start_id,
                "start_time": datetime.now().isoformat()
            })

            # 记录启动事件
            startup_log = f"[{datetime.now().strftime('%H:%M:%S')}] [Server/INFO]: Starting Minecraft server instance {instance_name}"
            log_manager.add_log(instance_name, start_id, startup_log)

            def read_output(pipe, prefix):
                for line in iter(pipe.readline, ""):
                    try:
                        log_manager.add_log(instance_name, start_id, line.strip())
                    except Exception as e:
                        print(f"Error logging output: {e}")

            threading.Thread(target=read_output, args=(process.stdout, "OUT"), daemon=True).start()
            threading.Thread(target=read_output, args=(process.stderr, "ERR"), daemon=True).start()

            print(f"Started instance {instance_name} with PID {process.pid} and log ID {start_id}")

        except Exception as e:
            print(f"Error starting instance: {e}")
            process.kill()
            raise

    def send_command(self, instance_name, command):
        """向指定实例发送命令"""
        instance_state = log_manager.get_instance_state(instance_name)
        if not instance_state:
            print(f"Instance {instance_name} is not running.")
            return

        pid = instance_state["pid"]

        # 使用进程的标准输入文件发送命令
        try:
            with open(f"/proc/{pid}/fd/0", "w") as stdin:
                stdin.write(f"{command}\n")
                stdin.flush()
            print(f"Sent command to {instance_name}: {command}")
        except Exception as e:
            print(f"Failed to send command: {e}")

    def stop_instance(self, instance_name):
        """关闭指定实例"""
        self.send_command(instance_name, "stop")

    def force_stop_instance(self, instance_name):
        """强制关闭指定实例"""
        instance_state = log_manager.get_instance_state(instance_name)
        if not instance_state:
            print(f"Instance {instance_name} is not running.")
            return

        pid = instance_state["pid"]

        # 强制终止进程
        try:
            subprocess.run(f"kill -9 {pid}", shell=True, check=True)
            print(f"Forcefully stopped instance: {instance_name}")
            log_manager.remove_instance_state(instance_name)
        except subprocess.CalledProcessError as e:
            print(f"Failed to forcefully stop instance {instance_name}: {e}")

    def list_instances(self):
        """列出所有实例"""
        instances = []
        for instance_dir in self.instances_dir.iterdir():
            if instance_dir.is_dir():
                instances.append(instance_dir.name)
        return instances