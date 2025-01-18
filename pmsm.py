import argparse
import requests

def main():
    parser = argparse.ArgumentParser(description="Python Minecraft Server Manager (PMSM)")
    parser.add_argument("action", choices=["start", "list", "stop", "force-stop", "cmd", "logs"], help="Action to perform")
    parser.add_argument("--instance", help="Instance name")
    parser.add_argument("--cmd", nargs="+", help="Minecraft command to send")
    parser.add_argument("--start-time", help="Log start time in format YYYY-MM-DD HH:MM:SS")

    args = parser.parse_args()

    base_url = "http://localhost:8000"

    if args.action == "start":
        if not args.instance:
            print("Error: --instance is required for 'start' action.")
            return
        response = requests.post(f"{base_url}/start/{args.instance}")
        print(response.json())
    elif args.action == "stop":
        if not args.instance:
            print("Error: --instance is required for 'stop' action.")
            return
        response = requests.post(f"{base_url}/stop/{args.instance}")
        print(response.json())
    elif args.action == "force-stop":
        if not args.instance:
            print("Error: --instance is required for 'force-stop' action.")
            return
        response = requests.post(f"{base_url}/force_stop/{args.instance}")
        print(response.json())
    elif args.action == "cmd":
        if not args.instance or not args.cmd:
            print("Error: --instance and --cmd are required for 'cmd' action.")
            return
        command = " ".join(args.cmd)
        # 发送 JSON 请求体
        response = requests.post(
            f"{base_url}/cmd/{args.instance}",
            json={"command": command}  # 注意这里是 JSON 格式
        )
        print(response.json())
    elif args.action == "logs":
        if not args.instance:
            print("Error: --instance is required for 'logs' action.")
            return
        params = {}
        if args.start_time:
            params["start_time"] = args.start_time
        response = requests.get(f"{base_url}/logs/{args.instance}", params=params)
        logs = response.json().get("logs", [])
        for log in logs:
            print(f"{log['timestamp']} [{log['level']}] {log['message']}")
    elif args.action == "list":
        # 列出实例的逻辑，可能需要通过API获取
        print("List of instances not implemented yet.")

if __name__ == "__main__":
    main()