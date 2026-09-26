"""
PramaanX — Error Response Schemas
"""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail

    model_config = {"json_schema_extra": {
        "example": {
            "error": {
                "code": "INVALID_DOCUMENT_IMAGE",
                "message": "The uploaded file could not be processed as a valid document image."
            }
        }
    }}
