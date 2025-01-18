import subprocess
import json
from pathlib import Path
import time
import os
from pmsm.config_manager import ConfigManager
import threading

class InstanceManager:
    def __init__(self, instances_dir="instances"):
        # 将 instances_dir 转换为绝对路径
        self.instances_dir = Path(instances_dir).resolve()
        print("Instances directory:", self.instances_dir)  # 打印实例目录路径
        if not self.instances_dir.exists():
            raise FileNotFoundError(f"Instances directory not found: {self.instances_dir}")
        
        # 状态文件路径
        self.state_file = self.instances_dir / "pmsm_state.json"
        self.processes = self._load_state()  # 从文件加载状态

    def _load_state(self):
        """从文件加载状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Warning: {self.state_file} is corrupted. Resetting state.")
        return {}

    def _save_state(self):
        """保存状态到文件"""
        # 只保存 PID
        state = {k: v for k, v in self.processes.items()}
        with open(self.state_file, "w") as f:
            json.dump(state, f, indent=4)
        print(f"Saved state to {self.state_file}: {self.processes}")  # 打印保存的状态

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

        def read_output(pipe, prefix):
            for line in iter(pipe.readline, ""):
                print(f"[{instance_name}][{prefix}] {line}", end="")

        threading.Thread(target=read_output, args=(process.stdout, "OUT")).start()
        threading.Thread(target=read_output, args=(process.stderr, "ERR")).start()

        self.processes[instance_name] = process.pid
        self._save_state()
        print(f"Started instance {instance_name} with PID {process.pid}")

    def send_command(self, instance_name, command):
        """向指定实例发送命令"""
        if instance_name not in self.processes:
            print(f"Instance {instance_name} is not running.")
            return

        pid = self.processes[instance_name]

        # 检查进程是否存在
        try:
            os.kill(pid, 0)
        except OSError:
            print(f"Instance {instance_name} is not running.")
            del self.processes[instance_name]
            self._save_state()
            return

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
        if instance_name not in self.processes:
            print(f"Instance {instance_name} is not running.")
            return

        # 获取进程 ID
        pid = self.processes[instance_name]["pid"]

        # 强制终止进程
        try:
            subprocess.run(f"kill -9 {pid}", shell=True, check=True)
            print(f"Forcefully stopped instance: {instance_name}")
            del self.processes[instance_name]  # 从状态中移除
            self._save_state()  # 保存状态
        except subprocess.CalledProcessError as e:
            print(f"Failed to forcefully stop instance {instance_name}: {e}")

    def list_instances(self):
        """列出所有实例"""
        instances = []
        for instance_dir in self.instances_dir.iterdir():
            if instance_dir.is_dir():
                instances.append(instance_dir.name)
        return instances