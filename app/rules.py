"""Reglas de negocio aplicadas después de la clasificación del modelo de IA.

El modelo de IA solo clasifica y sugiere; nunca ejecuta acciones externas.
Estas reglas son deterministas, explicables y fáciles de auditar, lo cual es
importante en un dominio como la atención de quejas de clientes.
"""

PRIORITY_BY_SEVERITY = {
    "baja": "baja",
    "media": "media",
    "alta": "urgente",
    "critica": "urgente",
}

CONFIDENCE_THRESHOLD = 0.80


def apply_business_rules(classification: dict) -> dict:
    """Recibe la salida del modelo y agrega `priority` y `needs_human_review`.

    Reglas:
    - Si confidence < 0.80 -> needs_human_review = True
    - Si severity == "critica" -> needs_human_review = True
    - Si is_complaint == False -> priority = "baja"
    - Si severity == "alta" -> priority = "urgente"
    """
    result = dict(classification)

    is_complaint = result.get("is_complaint", False)
    severity = result.get("severity", "baja")
    confidence = result.get("confidence", 0.0)

    if not is_complaint:
        priority = "baja"
    else:
        priority = PRIORITY_BY_SEVERITY.get(severity, "media")

    needs_human_review = confidence < CONFIDENCE_THRESHOLD or severity == "critica"

    result["priority"] = priority
    result["needs_human_review"] = needs_human_review
    return result
