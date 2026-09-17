"""API principal de ComplaintAgent AI.

Arquitectura:
    Cliente -> API (FastAPI, este archivo) -> ComplaintAgent -> Modelo de IA
    -> Reglas de negocio -> Respuesta JSON
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .agent import ComplaintAgent
from .models import ComplaintRequest, ComplaintResponse, ErrorDetail, ErrorResponse

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="ComplaintAgent AI",
    version="1.0.0",
    description="Agente de IA para recibir, clasificar y priorizar quejas de clientes.",
)

agent = ComplaintAgent()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Convierte los errores de validación de Pydantic/FastAPI en HTTP 400.

    Por defecto FastAPI devuelve 422; el requerimiento del proyecto pide 400
    con un cuerpo JSON estructurado cuando falta información obligatoria.
    """
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in error["loc"] if part != "body"),
            message=error["msg"],
        )
        for error in exc.errors()
    ]
    body = ErrorResponse(error="validation_error", details=details)
    return JSONResponse(status_code=400, content=body.model_dump())


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/agent/status")
def status() -> dict:
    return {
        "status": "running",
        "model_provider": os.getenv("MODEL_PROVIDER", "local"),
        "version": app.version,
    }


@app.post("/agent/complaint", response_model=ComplaintResponse)
def process_complaint(payload: ComplaintRequest) -> ComplaintResponse:
    return agent.process(payload)
