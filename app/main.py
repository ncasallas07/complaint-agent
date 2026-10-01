"""API principal de ComplaintAgent AI.

Arquitectura:
    Usuario -> Interfaz web (app/static) -> API (FastAPI, este archivo)
    -> ComplaintAgent -> Modelo de IA -> Reglas de negocio -> Respuesta JSON

La interfaz web es un cliente más de la API: solo consume
POST /agent/complaint mediante fetch() con rutas relativas.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

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

# Interfaz web (HTML/CSS/JS vanilla). Se sirve desde el mismo servidor, por lo
# que funciona igual en localhost y en la IP pública de EC2.
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


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


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    """Página principal: interfaz web de ComplaintAgent AI."""
    return FileResponse(STATIC_DIR / "index.html")


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
