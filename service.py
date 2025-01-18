# service.py
from fastapi import FastAPI, BackgroundTasks, Body, HTTPException
from pydantic import BaseModel
from pmsm.instance_manager import InstanceManager
from pmsm.log_manager import LogManager
import traceback
from datetime import datetime

app = FastAPI()
instance_manager = InstanceManager()
log_manager = LogManager()

# 定义请求体模型
class CommandModel(BaseModel):
    command: str

@app.post("/cmd/{instance_name}")
def send_command(instance_name: str, command_data: CommandModel):
    instance_manager.send_command(instance_name, command_data.command)
    return {"status": "command_sent"}

@app.post("/start/{instance_name}")
def start_instance(instance_name: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(instance_manager.start_instance, instance_name)
    return {"status": "starting"}

@app.post("/stop/{instance_name}")
def stop_instance(instance_name: str):
    instance_manager.stop_instance(instance_name)
    return {"status": "stopping"}

@app.post("/force_stop/{instance_name}")
def force_stop_instance(instance_name: str):
    instance_manager.force_stop_instance(instance_name)
    return {"status": "force_stopping"}

@app.get("/logs/{instance_name}")
async def get_logs(
    instance_name: str,
    start_id: int = None,
    start_id_min: int = None,
    start_id_max: int = None,
    start_time: str = None,
    end_time: str = None,
    search: str = None
):
    try:
        # 转换时间字符串为日期时间对象
        start_datetime = None
        end_datetime = None
        if start_time:
            try:
                start_datetime = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid start_time format")
        if end_time:
            try:
                end_datetime = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid end_time format")

        start_id_range = (start_id_min, start_id_max) if start_id_min and start_id_max else None
        
        # 直接传递搜索模式
        logs = log_manager.get_logs(
            instance_name=instance_name,
            start_id=start_id,
            start_id_range=start_id_range,
            start_time=start_datetime,
            end_time=end_datetime,
            search_pattern=search
        )
        
        if logs is None:
            logs = []

        return {"status": "success", "logs": logs}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# 添加错误处理
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    return {"status": "error", "detail": str(exc)}