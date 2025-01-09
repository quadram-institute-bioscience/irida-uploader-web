from ninja import Schema
from datetime import datetime
from typing import Optional

class UploadOut(Schema):
    id: int
    folder_name: str
    project_name: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

class NotificationOut(Schema):
    id: int
    title: str
    message: str
    type: str
    created_at: datetime
    read: bool 