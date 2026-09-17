# Arquitectura de ComplaintAgent AI

## Flujo general

```
Entrada JSON
   │
   ▼
Validación (Pydantic / FastAPI)
   │
   ▼
ComplaintAgent (app/agent.py)
   │
   ▼
Modelo de IA (app/classifier.py)
   │
   ▼
Reglas de negocio (app/rules.py)
   │
   ▼
Respuesta JSON estructurada
```

## Componentes

### 1. API (`app/main.py`)
Expone los endpoints HTTP con FastAPI y valida la forma de la solicitud
usando el modelo `ComplaintRequest` (Pydantic). Si falta un campo obligatorio
o el mensaje está vacío, la API responde `HTTP 400` con un cuerpo JSON
estructurado (`error`, `details`). La API no contiene lógica de negocio: solo
recibe la solicitud, delega en `ComplaintAgent` y devuelve la respuesta.

### 2. Agente (`app/agent.py`)
Orquesta el flujo completo:
1. Envía el mensaje al modelo de IA (`classifier.get_model()`).
2. Pasa el resultado del modelo a las reglas de negocio (`rules.py`).
3. Arma la respuesta final (`ComplaintResponse`).
4. Registra un evento de auditoría (log) y un registro simulado en
   `data/complaints.jsonl`, **sin** incluir el mensaje original ni el
   `customer_id`, para evitar guardar información sensible innecesaria.

### 3. Modelo de IA (`app/classifier.py`)
Capa completamente aislada de FastAPI. Expone una interfaz común
(`BaseComplaintModel.classify(message) -> dict`) con dos implementaciones:

- **`LocalHeuristicModel`** (por defecto): modelo ligero basado en palabras
  clave y reglas simples. No requiere GPU, ni modelos pesados, ni conexión a
  internet. Ideal para una instancia EC2 pequeña y para el desarrollo inicial
  con datos simulados.
- **`BedrockComplaintModel`**: implementación de referencia que invoca un
  modelo ligero de Amazon Bedrock (por ejemplo, Claude Haiku) para obtener la
  misma clasificación. Si la llamada falla (sin credenciales, sin conexión,
  error del servicio), hace *fallback* automático al modelo local para que el
  servicio nunca deje de responder.

El proveedor activo se selecciona con la variable de entorno
`MODEL_PROVIDER` (`local` o `bedrock`), sin cambiar el resto del código.

### 4. Reglas de negocio (`app/rules.py`)
Se ejecutan **después** del modelo de IA y son deterministas y auditables:

- Si `confidence < 0.80` → `needs_human_review = true`
- Si `severity == "critica"` → `needs_human_review = true`
- Si `is_complaint == false` → `priority = "baja"`
- Si `severity == "alta"` → `priority = "urgente"`

El modelo de IA **nunca** ejecuta acciones externas: solo clasifica y
sugiere una acción recomendada (texto). Cualquier acción real (escalar,
notificar, reembolsar) queda a cargo de un humano o de un sistema externo
que consuma la respuesta del agente.

### 5. Modelos de datos (`app/models.py`)
Define los esquemas Pydantic de entrada (`ComplaintRequest`), salida
(`ComplaintResponse`) y error (`ErrorResponse`).

## Por qué esta arquitectura

- **Separación de responsabilidades**: la API, el agente, el modelo y las
  reglas de negocio son módulos independientes. Se puede reemplazar el
  modelo de IA sin tocar la API, o cambiar las reglas de negocio sin tocar
  el modelo.
- **Simplicidad**: no hay colas de mensajes, bases de datos externas ni
  microservicios adicionales. Es una arquitectura de un solo servicio,
  adecuada para un proyecto académico y fácil de explicar en una
  presentación.
- **Preparada para AWS**: al ser una aplicación FastAPI estándar servida con
  Uvicorn, se ejecuta igual en local que en una instancia EC2. Los logs se
  imprimen a `stdout`, formato compatible con el agente de CloudWatch Logs.
