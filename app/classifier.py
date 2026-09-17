"""Capa del modelo de IA.

Este módulo aísla por completo la lógica de clasificación del resto de la
aplicación. `agent.py` solo conoce el método `classify(message) -> dict` y
nunca sabe si, por debajo, se está usando un modelo local ligero (heurístico,
usado por defecto) o un modelo de Amazon Bedrock. Esto permite reemplazar el
modelo de IA sin tocar el resto del proyecto.
"""
from __future__ import annotations

import logging
import os
from typing import Dict

logger = logging.getLogger("complaint_agent.classifier")

CATEGORY_KEYWORDS: Dict[str, list] = {
    "entrega": [
        "entrega", "envio", "envío", "pedido", "retraso", "tarde",
        "paquete", "llego", "llegó", "transportadora", "despacho", "domicilio",
    ],
    "facturacion": [
        "factura", "cobro", "cobraron", "pago", "tarjeta", "reembolso",
        "dinero", "precio", "cargo", "facturacion", "facturación", "cuenta cobrada",
    ],
    "producto": [
        "producto", "dañado", "defectuoso", "roto", "calidad", "no funciona",
        "golpeado", "incompleto", "talla", "vencido", "falla",
    ],
    "servicio": [
        "atencion", "atención", "agente", "servicio al cliente", "soporte",
        "trato", "grosero", "amable", "asesor", "linea de ayuda", "línea de ayuda",
    ],
}

CATEGORY_LABELS = {
    "entrega": "la entrega del pedido",
    "facturacion": "la facturación o los cobros",
    "producto": "el estado o calidad del producto",
    "servicio": "la atención al cliente",
    "otro": "un tema general",
}

NEGATIVE_WORDS = [
    "mal", "pesimo", "pésimo", "terrible", "molesto", "inconforme", "enojado",
    "frustrado", "nunca", "horrible", "decepcionado", "indignado", "harto",
    "insatisfecho", "queja", "problema", "nadie", "solucion",
]

POSITIVE_WORDS = [
    "gracias", "excelente", "genial", "satisfecho", "feliz", "contento", "buen",
]

CRITICAL_WORDS = [
    "demanda", "abogado", "denuncia", "fraude", "estafa", "autoridades",
    "accion legal", "acción legal",
]

NON_COMPLAINT_INDICATORS = [
    "quisiera saber", "podrian informarme", "podrían informarme",
    "me gustaria saber", "me gustaría saber", "como puedo", "cómo puedo",
    "horario de atencion", "horario de atención", "informacion sobre",
    "información sobre", "tienen disponible", "hacen envios a", "hacen envíos a",
]


def _count_matches(text: str, words: list) -> int:
    return sum(1 for word in words if word in text)


def _detect_category(text: str):
    best_category = "otro"
    best_score = 0
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = _count_matches(text, keywords)
        if score > best_score:
            best_score = score
            best_category = category
    return best_category, best_score


def _estimate_confidence(category_score: int, neg_count: int, pos_count: int,
                          critical: bool, is_question: bool) -> float:
    confidence = 0.55
    confidence += min(category_score, 3) * 0.12
    confidence += min(neg_count, 3) * 0.06
    if critical:
        confidence += 0.10
    if is_question and category_score == 0 and neg_count == 0:
        confidence += 0.15
    if category_score == 0 and neg_count == 0 and pos_count == 0 and not is_question:
        confidence -= 0.15
    confidence = max(0.50, min(confidence, 0.97))
    return round(confidence, 2)


def _build_summary(is_complaint: bool, category: str, severity: str) -> str:
    if not is_complaint:
        return "El mensaje no representa una queja formal del cliente."
    category_text = CATEGORY_LABELS.get(category, "un tema general")
    if severity == "critica":
        return f"Cliente reporta una situación crítica relacionada con {category_text}."
    if severity == "alta":
        return f"Cliente inconforme por un problema relacionado con {category_text}."
    return f"Cliente presenta una observación relacionada con {category_text}."


def _recommend_action(is_complaint: bool, category: str, severity: str) -> str:
    if not is_complaint:
        return "No se requiere acción. Posible consulta o mensaje informativo."
    if severity == "critica":
        return "Escalar de inmediato al área correspondiente y notificar a un supervisor."

    actions = {
        "entrega": "Escalar el caso al área de logística y dar seguimiento al envío.",
        "facturacion": "Derivar el caso al área de facturación para revisión de cobros.",
        "producto": "Gestionar el reemplazo o devolución del producto con el área de calidad.",
        "servicio": "Escalar el caso al área de servicio al cliente para seguimiento.",
        "otro": "Revisar el caso manualmente para determinar el área responsable.",
    }
    return actions.get(category, actions["otro"])


class BaseComplaintModel:
    """Interfaz que debe cumplir cualquier modelo de clasificación de quejas."""

    def classify(self, message: str) -> dict:
        raise NotImplementedError


class LocalHeuristicModel(BaseComplaintModel):
    """Modelo ligero basado en reglas y palabras clave.

    No depende de librerías de machine learning ni de un modelo local
    pesado. Sirve como implementación por defecto y como respaldo (fallback)
    cuando el modelo remoto (por ejemplo, Amazon Bedrock) no está disponible.
    """

    def classify(self, message: str) -> dict:
        text = message.lower()

        category, category_score = _detect_category(text)
        neg_count = _count_matches(text, NEGATIVE_WORDS)
        pos_count = _count_matches(text, POSITIVE_WORDS)
        critical = _count_matches(text, CRITICAL_WORDS) > 0
        is_question = _count_matches(text, NON_COMPLAINT_INDICATORS) > 0

        if pos_count > neg_count:
            sentiment = "positivo"
        elif neg_count > pos_count:
            sentiment = "negativo"
        else:
            sentiment = "neutral"

        is_complaint = True
        if is_question and neg_count == 0 and not critical:
            is_complaint = False
        elif neg_count == 0 and category_score == 0 and not critical:
            is_complaint = False

        if not is_complaint:
            severity = "baja"
            category = "otro"
        elif critical:
            severity = "critica"
        elif neg_count >= 2 or category_score >= 2:
            severity = "alta"
        elif neg_count == 1 or category_score == 1:
            severity = "media"
        else:
            severity = "baja"

        confidence = _estimate_confidence(category_score, neg_count, pos_count, critical, is_question)
        summary = _build_summary(is_complaint, category, severity)
        recommended_action = _recommend_action(is_complaint, category, severity)

        return {
            "is_complaint": is_complaint,
            "category": category if is_complaint else "otro",
            "severity": severity,
            "sentiment": sentiment,
            "summary": summary,
            "recommended_action": recommended_action,
            "confidence": confidence,
        }


class BedrockComplaintModel(BaseComplaintModel):
    """Modelo que delega la clasificación a Amazon Bedrock.

    Se mantiene aislado de FastAPI: solo expone `classify`. Si la llamada al
    modelo remoto falla (por ejemplo, sin credenciales configuradas en la
    instancia EC2), se hace fallback automático al modelo local ligero para
    que el servicio nunca deje de responder.
    """

    def __init__(self, model_id: str = None, region: str = None):
        import boto3  # import diferido: no es obligatorio si no se usa Bedrock

        self.model_id = model_id or os.getenv(
            "BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"
        )
        self.region = region or os.getenv("AWS_REGION", "us-east-1")
        self.client = boto3.client("bedrock-runtime", region_name=self.region)
        self.fallback = LocalHeuristicModel()

    def classify(self, message: str) -> dict:
        import json

        prompt = (
            "Eres un asistente que clasifica quejas de clientes. "
            "Responde EXCLUSIVAMENTE con un JSON con las llaves: "
            "is_complaint (bool), category (entrega|facturacion|producto|servicio|otro), "
            "severity (baja|media|alta|critica), sentiment (positivo|neutral|negativo), "
            "summary (string breve), recommended_action (string breve), "
            "confidence (float entre 0 y 1).\n\n"
            f"Mensaje del cliente: {message}"
        )
        try:
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "messages": [{"role": "user", "content": prompt}],
            })
            raw_response = self.client.invoke_model(modelId=self.model_id, body=body)
            payload = json.loads(raw_response["body"].read())
            text_output = payload["content"][0]["text"]
            result = json.loads(text_output)
            return {
                "is_complaint": bool(result["is_complaint"]),
                "category": result["category"],
                "severity": result["severity"],
                "sentiment": result["sentiment"],
                "summary": result["summary"],
                "recommended_action": result["recommended_action"],
                "confidence": float(result["confidence"]),
            }
        except Exception as exc:  # noqa: BLE001 - cualquier fallo cae al modelo local
            logger.warning("Fallo al invocar Bedrock, usando modelo local. Detalle: %s", exc)
            return self.fallback.classify(message)


_model_instance: BaseComplaintModel = None


def get_model() -> BaseComplaintModel:
    """Fábrica del modelo activo, seleccionado mediante MODEL_PROVIDER."""
    global _model_instance
    if _model_instance is not None:
        return _model_instance

    provider = os.getenv("MODEL_PROVIDER", "local").lower()
    if provider == "bedrock":
        try:
            _model_instance = BedrockComplaintModel()
        except Exception as exc:  # noqa: BLE001
            logger.warning("No se pudo inicializar Bedrock, usando modelo local. Detalle: %s", exc)
            _model_instance = LocalHeuristicModel()
    else:
        _model_instance = LocalHeuristicModel()
    return _model_instance
