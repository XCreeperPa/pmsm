import subprocess
import json
from pathlib import Path
from pmsm.config_manager import ConfigManager

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
        with open(self.state_file, "w") as f:
            json.dump(self.processes, f, indent=4)
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

        # 获取 JDK 路径（转换为绝对路径）
        jdk_path = (instance_dir / config["jdk_path"]).resolve()
        print("JDK path:", jdk_path)  # 打印 JDK 路径
        if not jdk_path.exists():
            raise FileNotFoundError(f"JDK not found: {jdk_path}")

        # 获取服务器 JAR 路径（转换为绝对路径）
        server_jar = (instance_dir / config["server_jar"]).resolve()
        print("Server JAR path:", server_jar)  # 打印服务器 JAR 路径
        if not server_jar.exists():
            raise FileNotFoundError(f"Server JAR not found: {server_jar}")

        # 启动服务器
        command = f'"{jdk_path}" -jar "{server_jar}"'
        print("Command:", command)  # 打印执行的命令
        process = subprocess.Popen(
            command,
            shell=True,
            cwd=server_jar.parent,
            stdin=subprocess.PIPE,  # 启用标准输入
            stdout=subprocess.PIPE,  # 启用标准输出
            stderr=subprocess.PIPE,  # 启用标准错误
            text=True  # 支持文本输入
        )
        self.processes[instance_name] = process.pid  # 保存进程 ID
        self._save_state()  # 保存状态
        print(f"Started instance: {instance_name}")

        # 实时输出服务器日志
        def log_output(stream, prefix):
            for line in iter(stream.readline, ''):
                print(f"[{prefix}] {line}", end='')

        import threading
        threading.Thread(target=log_output, args=(process.stdout, "STDOUT"), daemon=True).start()
        threading.Thread(target=log_output, args=(process.stderr, "STDERR"), daemon=True).start()

    def send_command(self, instance_name, command):
        """向指定实例发送命令"""
        if instance_name not in self.processes:
            print(f"Instance {instance_name} is not running.")
            return

        # 获取进程 ID
        pid = self.processes[instance_name]

        # 检查进程是否仍在运行
        try:
            subprocess.run(f"kill -0 {pid}", shell=True, check=True)  # 检查进程是否存在
        except subprocess.CalledProcessError:
            print(f"Instance {instance_name} is not running.")
            del self.processes[instance_name]  # 清理已退出的进程
            self._save_state()  # 保存状态
            return

        # 发送命令
        try:
            subprocess.run(f"echo '{command}' > /proc/{pid}/fd/0", shell=True, check=True)
            print(f"Sent command to instance {instance_name}: {command}")
        except Exception as e:
            print(f"Failed to send command to instance {instance_name}: {e}")

    def stop_instance(self, instance_name):
        """关闭指定实例"""
        if instance_name not in self.processes:
            print(f"Instance {instance_name} is not running.")
            return

        # 获取进程 ID
        pid = self.processes[instance_name]

        # 发送 stop 命令
        try:
            subprocess.run(f"kill -TERM {pid}", shell=True, check=True)
            print(f"Sent stop signal to instance: {instance_name}")
            del self.processes[instance_name]  # 从状态中移除
            self._save_state()  # 保存状态
        except subprocess.CalledProcessError as e:
            print(f"Failed to stop instance {instance_name}: {e}")

    def force_stop_instance(self, instance_name):
        """强制关闭指定实例"""
        if instance_name not in self.processes:
            print(f"Instance {instance_name} is not running.")
            return

        # 获取进程 ID
        pid = self.processes[instance_name]

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