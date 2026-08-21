from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, validator
import storage

router = APIRouter()

class MessageCreate(BaseModel):
    content: str
    mood: str = "未知"

    @validator('content')
    def validate_content(cls, v):
        stripped = v.strip()
        if len(stripped) < 1:
            raise ValueError('内容不能为空')
        if len(stripped) > 500:
            raise ValueError('内容不能超过500字')
        return stripped

@router.post("/messages")
async def create_message(data: MessageCreate):
    return storage.create(data.content, data.mood)

@router.get("/messages")
async def get_messages(
    page: int = Query(1, ge=1, description="页码，从1开始"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数，最多100")
):
    """获取所有倾诉（支持分页）"""
    return storage.get_all(page, page_size)

@router.get("/messages/{msg_id}")
async def get_message(msg_id: int):
    msg = storage.get_by_id(msg_id)
    if not msg:
        raise HTTPException(status_code=404, detail="该倾诉不存在")
    return msg

@router.delete("/messages/{msg_id}")
async def delete_message(msg_id: int):
    """删除一条倾诉（管理功能）"""
    success = storage.delete(msg_id)
    if not success:
        raise HTTPException(status_code=404, detail="该倾诉不存在")
    return {"ok": True, "message": "删除成功"}