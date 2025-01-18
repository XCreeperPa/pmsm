# Python Minecraft Server Manager (PMSM)

一个基于 FastAPI 的 Minecraft 服务器管理工具，支持多实例管理、命令发送和日志查询。

## 功能特性

- 多服务器实例管理
- 日志持久化存储
  - 按实例和启动时间分表存储
  - 支持结构化日志解析
  - 自动识别 Minecraft 日志格式
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

### 停止实例
```bash
python pmsm.py stop --instance <实例名称>
```

### 强制停止实例
```bash
python pmsm.py force-stop --instance <实例名称>
```

### 日志管理

#### 查看和搜索日志

可选参数：

- `--start-id <ID或ID范围>`
  - 类型：整数或范围（例如：'3' 或 '1-5'）
  - 默认值：最后一次启动的ID
  - 用途：按启动次数筛选日志
  - 说明：可以指定单个ID或ID范围，例如 `--start-id 3` 或 `--start-id 1-5`

- `--start-time <时间戳>`
  - 类型：字符串，格式为 "YYYY-MM-DD HH:MM:SS"
  - 默认值：无（不过滤）
  - 用途：设置日志查询的起始时间
  - 示例：`--start-time "2024-01-20 20:00:00"`

- `--end-time <时间戳>`
  - 类型：字符串，格式为 "YYYY-MM-DD HH:MM:SS"
  - 默认值：无（不过滤）
  - 用途：设置日志查询的结束时间
  - 示例：`--end-time "2024-01-20 21:00:00"`

- `--search <搜索模式>`
  - 类型：字符串，支持通配符
  - 默认值：无（不过滤）
  - 用途：在日志内容中搜索指定模式
  - 通配符：使用 `*` 表示任意字符
  - 转义：使用 `\*` 表示字面值的星号
  - 示例：
    - `--search "Player*joined"` 匹配所有包含"Player"开头"joined"结尾的日志
    - `--search "*error*"` 匹配所有包含"error"的日志
    - `--search "test\*test"` 匹配包含"test*test"的日志

**示例用法**

- 查看最后一次启动的所有日志：
  ```bash
  logviewer
  ```

- 查看指定时间范围的日志：
  ```bash
  logviewer --start-time "2024-01-20 20:00:00" --end-time "2024-01-20 21:00:00"
  ```

- 查看指定启动ID范围的日志：
  ```bash
  logviewer --start-id 1-5
  ```

- 搜索包含特定内容的日志：
  ```bash
  logviewer --search "*error*"
  ```

- 组合多个条件：
  ```bash
  logviewer --start-id 3 --start-time "2024-01-20 20:00:00" --search "*error*"
  ```

**注意事项**

- 所有时间参数都基于系统的 UTC+8 时区
- 日志搜索对大小写敏感
- 通配符只在 `--search` 参数中有效
- 多个过滤条件是"与"的关系，必须同时满足
- 建议先使用较宽松的过滤条件，然后逐步缩小范围


## API 接口

- `POST /start/{instance_name}` - 启动实例
- `POST /stop/{instance_name}` - 停止实例
- `POST /force_stop/{instance_name}` - 强制停止实例
- `POST /cmd/{instance_name}` - 发送命令
- `GET /logs/{instance_name}` - 获取日志

## 注意事项

1. 请确保实例目录下有正确的 JDK 和服务器 JAR 文件
2. 强制停止可能导致数据丢失，请谨慎使用