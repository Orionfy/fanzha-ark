from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from . import storage

router = APIRouter()

class MessageCreate(BaseModel):
    content: str
    mood: str = "未知"

@router.post("/messages")
async def create_message(data: MessageCreate):
    if not data.content or len(data.content.strip()) < 1:
        raise HTTPException(status_code=400, detail="内容不能为空")
    return storage.create(data.content.strip(), data.mood)

@router.get("/messages")
async def get_messages():
    return storage.get_all()

@router.get("/messages/{msg_id}")
async def get_message(msg_id: int):
    msg = storage.get_by_id(msg_id)
    if not msg:
        raise HTTPException(status_code=404, detail="该倾诉不存在")
    return msg