# Python Minecraft Server Manager (PMSM)

一个基于 FastAPI 的 Minecraft 服务器管理工具，支持多实例管理、命令发送和日志查询。

## 功能特性

- 多服务器实例管理
- 日志持久化存储
- RESTful API 接口
- 命令行客户端
- 状态持久化

## 架构设计

- 后端：FastAPI 服务器，负责实例管理和日志存储
- 前端：命令行工具，通过 HTTP 请求与后端交互

## 安装要求

- Python 3.6+
- Linux 系统
- 依赖包：
  - fastapi
  - uvicorn
  - requests
  - sqlite3

## 目录结构

```
instances/
├── my_server/              # 实例目录
│   ├── instance.json      # 实例配置
│   ├── server.jar         # 服务器主程序
│   ├── jdk/              # Java运行环境
│   └── server/           # 服务器数据目录
├── pmsm_state.json       # PMSM状态文件
└── logs.db               # 日志数据库
```

## 配置文件

每个实例需要一个 `instance.json` 配置文件：

```json
{
    "jdk_path": "jdk",
    "server_jar": "server.jar"
}
```

配置项说明：
- `jdk_path`: JDK路径（相对于实例目录）
- `server_jar`: 服务器JAR文件路径

## 使用方法

### 启动服务端
```bash
uvicorn service:app --reload
```

### 列出所有实例
```bash
python pmsm.py list
```

### 启动实例
```bash
python pmsm.py start --instance <实例名称>
```

### 发送命令
```bash
python pmsm.py cmd --instance <实例名称> --cmd <命令>
```

### 查看日志
```bash
python pmsm.py logs --instance <实例名称> [--start-time "YYYY-MM-DD HH:MM:SS"]
```

### 停止实例
```bash
python pmsm.py stop --instance <实例名称>
```

### 强制停止实例
```bash
python pmsm.py force-stop --instance <实例名称>
```

## API 接口

- `POST /start/{instance_name}` - 启动实例
- `POST /stop/{instance_name}` - 停止实例
- `POST /force_stop/{instance_name}` - 强制停止实例
- `POST /cmd/{instance_name}` - 发送命令
- `GET /logs/{instance_name}` - 获取日志

## 注意事项

1. 请确保实例目录下有正确的 JDK 和服务器 JAR 文件
2. 命令发送功能依赖 Linux 的 /proc 文件系统
3. 强制停止可能导致数据丢失，请谨慎使用
