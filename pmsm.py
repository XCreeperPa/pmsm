import argparse
import requests
import sys
import json

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
        try:
            params = {}
            if args.start_time:
                params["start_time"] = args.start_time
            response = requests.get(f"{base_url}/logs/{args.instance}", params=params)
            response.raise_for_status()  # 检查 HTTP 状态码
            
            data = response.json()
            if not isinstance(data, dict):
                print(f"Error: Unexpected response format: {data}")
                return
                
            logs = data.get("logs", [])
            if not logs:
                print("No logs found.")
                return
                
            for log in logs:
                try:
                    print(f"[{log['timestamp']}] [{log['thread']}/{log['level']}]: {log['message']}")
                except KeyError as e:
                    print(f"Error: Missing field in log entry: {e}")
                    continue
                    
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to server: {e}")
        except json.JSONDecodeError as e:
            print(f"Error decoding server response: {e}")
            print(f"Response content: {response.text}")
        except Exception as e:
            print(f"Unexpected error: {e}")
            
    elif args.action == "list":
        # 列出实例的逻辑，可能需要通过API获取
        print("List of instances not implemented yet.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)