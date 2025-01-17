import argparse
import os
from pathlib import Path
from pmsm.instance_manager import InstanceManager

def main():
    # 设置工作目录为项目根目录
    project_root = Path(__file__).parent
    os.chdir(project_root)

    parser = argparse.ArgumentParser(description="Python Minecraft Server Manager (PMSM)")
    parser.add_argument("action", choices=["start", "list", "stop", "force-stop", "cmd"], help="Action to perform")
    parser.add_argument("--instance", help="Instance name to start")
    parser.add_argument("--cmd", nargs="+", help="Minecraft command to send to the instance")
    
    args = parser.parse_args()
    manager = InstanceManager()

    if args.action == "start":
        if not args.instance:
            print("Error: --instance is required for 'start' action.")
            return
        manager.start_instance(args.instance)
    elif args.action == "stop":
        if not args.instance:
            print("Error: --instance is required for 'stop' action.")
            return
        manager.stop_instance(args.instance)
    elif args.action == "force-stop":
        if not args.instance:
            print("Error: --instance is required for 'force-stop' action.")
            return
        manager.force_stop_instance(args.instance)
    elif args.action == "cmd":
        if not args.instance or not args.cmd:
            print("Error: --instance and --cmd are required for 'cmd' action.")
            return
        # 将 --cmd 的多个值拼接为一个完整的命令
        command = " ".join(args.cmd)
        manager.send_command(args.instance, command)
    elif args.action == "list":
        instances = manager.list_instances()
        print("Available instances:")
        for instance in instances:
            print(f" - {instance}")

if __name__ == "__main__":
    main()
