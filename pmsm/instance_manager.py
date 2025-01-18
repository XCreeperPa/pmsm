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
        
        # 状态文件路径
        self.state_file = self.instances_dir / "pmsm_state.json"
        self.processes = self._load_state()  # 从文件加载状态

    def _load_state(self):
        """从文件加载状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r") as f:
                    state = json.load(f)
                    # 验证数据格式
                    for key, value in state.items():
                        if not isinstance(value, dict) or "pid" not in value or "start_id" not in value:
                            print(f"Warning: Invalid state format for {key}")
                            continue
                    return state
            except json.JSONDecodeError:
                print(f"Warning: {self.state_file} is corrupted. Resetting state.")
        return {}

    def _save_state(self):
        """保存状态到文件"""
        try:
            # 确保所有进程状态都包含必要的字段
            for instance, state in self.processes.items():
                if not isinstance(state, dict):
                    self.processes[instance] = {
                        "pid": state if isinstance(state, int) else None,
                        "start_id": None
                    }
            
            with open(self.state_file, "w") as f:
                json.dump(self.processes, f, indent=4)
            print(f"Saved state to {self.state_file}: {self.processes}")
        except Exception as e:
            print(f"Error saving state: {e}")

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
            
            # 保存进程状态，确保包含所有必要字段
            self.processes[instance_name] = {
                "pid": process.pid,
                "start_id": start_id,
                "start_time": datetime.now().isoformat()
            }
            self._save_state()

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
            # 清理
            process.kill()
            if instance_name in self.processes:
                del self.processes[instance_name]
            raise

    def send_command(self, instance_name, command):
        """向指定实例发送命令"""
        if instance_name not in self.processes:
            print(f"Instance {instance_name} is not running.")
            return

        pid = self.processes[instance_name]["pid"]

        # 检查进程是否存在
        '''
        try:
            os.kill(pid, 0)
        except OSError:
            print(f"Instance {instance_name} is not running.")
            del self.processes[instance_name]
            self._save_state()
            return
        '''
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