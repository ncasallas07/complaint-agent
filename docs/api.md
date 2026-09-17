# API de ComplaintAgent AI

Base URL local por defecto: `http://localhost:8000`

## GET /health

Verifica que el servicio esté activo.

**Respuesta 200**
```json
{ "status": "ok" }
```

## GET /agent/status

Devuelve información básica del estado del agente.

**Respuesta 200**
```json
{
  "status": "running",
  "model_provider": "local",
  "version": "1.0.0"
}
```

## POST /agent/complaint

Recibe una queja y devuelve la clasificación estructurada.

### Solicitud

| Campo        | Tipo   | Obligatorio | Descripción                          |
|--------------|--------|-------------|---------------------------------------|
| complaint_id | string | Sí          | Identificador único de la queja       |
| customer_id  | string | No          | Identificador del cliente             |
| channel      | string | Sí          | Canal de origen (web, app, email...)  |
| message      | string | Sí          | Texto de la queja (no puede ir vacío) |

```json
{
  "complaint_id": "CMP-001",
  "customer_id": "CUS-1001",
  "channel": "web",
  "message": "Mi pedido lleva tres días de retraso y nadie me da una solución."
}
```

### Respuesta 200

```json
{
  "complaint_id": "CMP-001",
  "is_complaint": true,
  "category": "entrega",
  "severity": "alta",
  "sentiment": "negativo",
  "priority": "urgente",
  "summary": "Cliente inconforme por un problema relacionado con la entrega del pedido.",
  "recommended_action": "Escalar el caso al área de logística y dar seguimiento al envío.",
  "confidence": 0.85,
  "needs_human_review": false
}
```

Valores posibles:
- `category`: `entrega`, `facturacion`, `producto`, `servicio`, `otro`
- `severity`: `baja`, `media`, `alta`, `critica`
- `sentiment`: `positivo`, `neutral`, `negativo`
- `priority`: `baja`, `media`, `urgente`

### Respuesta 400 (validación)

Se devuelve cuando falta un campo obligatorio o el mensaje está vacío.

```json
{
  "error": "validation_error",
  "details": [
    { "field": "message", "message": "Field required" }
  ]
}
```
