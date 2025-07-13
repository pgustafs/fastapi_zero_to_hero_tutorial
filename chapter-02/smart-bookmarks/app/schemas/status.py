from datetime import datetime
from pydantic import BaseModel, Field


# Define a Pydantic model for the response structure
class StatusResponse(BaseModel):
    current_time: datetime = Field(
        ..., json_schema_extra={"example": "2025-07-13T12:00:00.000000Z"}
    )
    database_url: str = Field(
        ..., json_schema_extra={"example": "sqlite:///./b********.db"}
    )
