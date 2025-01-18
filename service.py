# service.py
from fastapi import FastAPI, BackgroundTasks, Body
from pydantic import BaseModel
from pmsm.instance_manager import InstanceManager
from pmsm.log_manager import LogManager

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
def get_logs(instance_name: str, start_time: str = None):
    logs = log_manager.get_logs(instance_name, start_time)
    return {"logs": logs}