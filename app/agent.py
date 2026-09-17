"""ComplaintAgent: orquesta clasificación (IA) + reglas de negocio.

Flujo: ComplaintRequest -> modelo de IA (classifier.py) -> reglas de negocio
(rules.py) -> ComplaintResponse. El agente también registra un evento por
cada queja procesada, sin incluir el texto del mensaje ni el customer_id,
para evitar guardar información sensible innecesaria en los logs.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from . import rules
from .classifier import BaseComplaintModel, get_model
from .models import ComplaintRequest, ComplaintResponse

logger = logging.getLogger("complaint_agent")

DATA_DIR = Path(os.getenv("DATA_DIR", str(Path(__file__).resolve().parent.parent / "data")))
COMPLAINTS_LOG_PATH = DATA_DIR / "complaints.jsonl"


class ComplaintAgent:
    def __init__(self, model: BaseComplaintModel = None):
        self.model = model or get_model()

    def process(self, request: ComplaintRequest) -> ComplaintResponse:
        classification = self.model.classify(request.message)
        classification = rules.apply_business_rules(classification)

        response = ComplaintResponse(complaint_id=request.complaint_id, **classification)

        self._log_event(request, response)
        self._persist_event(request, response)

        return response

    def _log_event(self, request: ComplaintRequest, response: ComplaintResponse) -> None:
        logger.info(json.dumps({
            "event": "complaint_processed",
            "complaint_id": request.complaint_id,
            "channel": request.channel,
            "category": response.category,
            "severity": response.severity,
            "priority": response.priority,
            "needs_human_review": response.needs_human_review,
        }))

    def _persist_event(self, request: ComplaintRequest, response: ComplaintResponse) -> None:
        """Guarda un registro no sensible en data/complaints.jsonl.

        No incluye el mensaje original ni el customer_id. Puede desactivarse
        con PERSIST_COMPLAINTS=false (usado en las pruebas automatizadas).
        """
        if os.getenv("PERSIST_COMPLAINTS", "true").lower() != "true":
            return

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "complaint_id": request.complaint_id,
            "channel": request.channel,
            "is_complaint": response.is_complaint,
            "category": response.category,
            "severity": response.severity,
            "sentiment": response.sentiment,
            "priority": response.priority,
            "confidence": response.confidence,
            "needs_human_review": response.needs_human_review,
        }
        try:
            COMPLAINTS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(COMPLAINTS_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as exc:
            logger.warning("No se pudo escribir en el registro de quejas: %s", exc)
