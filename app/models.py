"""Modelos Pydantic de entrada y salida del agente."""
from typing import List, Optional

from pydantic import BaseModel, field_validator


class ComplaintRequest(BaseModel):
    """Estructura de la solicitud recibida en POST /agent/complaint."""

    complaint_id: str
    customer_id: Optional[str] = None
    channel: str
    message: str

    @field_validator("complaint_id")
    @classmethod
    def complaint_id_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("complaint_id no puede estar vacío")
        return value

    @field_validator("channel")
    @classmethod
    def channel_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("channel no puede estar vacío")
        return value

    @field_validator("message")
    @classmethod
    def message_not_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("message no puede estar vacío")
        return value


class ComplaintResponse(BaseModel):
    """Estructura de la respuesta devuelta por el agente."""

    complaint_id: str
    is_complaint: bool
    category: str
    severity: str
    sentiment: str
    priority: str
    summary: str
    recommended_action: str
    confidence: float
    needs_human_review: bool


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ErrorResponse(BaseModel):
    error: str
    details: List[ErrorDetail] = []
