from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreateLinkRequest(BaseModel):
    long_url: str


class CreateLinkResponse(BaseModel):
    code: str
    short_url: str
    long_url: str


class LinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    short_url: str
    long_url: str
    click_count: int
    status: int
    created_at: datetime
