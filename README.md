# ComplaintAgent AI

Proyecto académico para la asignatura **Electiva III - Cloud Computing**.

## 1. Problema

Las empresas reciben quejas de clientes por múltiples canales (web, app,
correo, teléfono) en texto libre. Clasificarlas manualmente (categoría,
severidad, sentimiento, prioridad) es lento y depende del criterio de cada
persona, lo que retrasa la atención de casos urgentes.

## 2. Objetivo

Construir un agente de inteligencia artificial, expuesto como API, que:

1. Reciba una queja en formato JSON.
2. Valide los campos obligatorios.
3. Analice el texto con un modelo de IA ligero.
4. Determine categoría, severidad, sentimiento y prioridad.
5. Genere un resumen y una acción recomendada.
6. Indique si el caso necesita revisión humana.
7. Devuelva todo en una respuesta JSON estructurada, lista para integrarse
   con otros sistemas (CRM, mesa de ayuda, dashboards).

Además, incluye una **interfaz web** sencilla (HTML/CSS/JavaScript) para
registrar una queja desde un formulario y ver el resultado del análisis sin
usar Swagger.

## 3. Arquitectura

```
Usuario → Interfaz web (HTML/CSS/JS) → API Python (FastAPI) → ComplaintAgent
        → Modelo de IA → Reglas de negocio → Respuesta JSON
```

La interfaz web es un cliente más de la API: envía la queja a
`POST /agent/complaint` con `fetch()` y muestra la respuesta JSON de forma
visual. Otros sistemas pueden seguir consumiendo la API directamente.

El detalle de cada componente está en [docs/architecture.md](docs/architecture.md).

## 4. Tecnologías

- Python 3.11+ (probado con Python 3.14.7)
- FastAPI + Uvicorn
- HTML, CSS y JavaScript *vanilla* para la interfaz web (sin frameworks ni
  dependencias adicionales)
- Pydantic (validación de datos)
- JSON / JSONL como formato de datos e intercambio
- AWS EC2 (despliegue)
- Amazon Bedrock (modelo de IA ligero, opcional) con *fallback* a un modelo
  heurístico local que no requiere GPU ni modelos pesados
- Git / GitHub
- Amazon CloudWatch Logs (opcional, para centralizar logs de la instancia)

## 5. Estructura del proyecto

```
complaint-agent/
├── app/
│   ├── main.py         # Endpoints FastAPI
│   ├── agent.py         # Orquestador: modelo + reglas + logging
│   ├── classifier.py     # Capa del modelo de IA (local y Bedrock)
│   ├── rules.py          # Reglas de negocio
│   ├── models.py         # Esquemas Pydantic (request/response/error)
│   └── static/           # Interfaz web (servida en /)
│       ├── index.html
│       ├── style.css
│       └── script.js
├── data/
│   ├── complaints.jsonl   # Registro simulado de quejas procesadas
│   └── examples.json      # Ejemplos de solicitudes de prueba
├── tests/
│   ├── test_agent.py
│   ├── test_classifier.py
│   └── test_frontend.py
├── docs/
│   ├── architecture.md
│   └── api.md
├── examples/
│   ├── complaint_input.json
│   └── complaint_output.json
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 6. Instalación

Requisitos: Python 3.11 o superior (probado con Python 3.14.7).

```bash
git clone <url-del-repositorio>
cd complaint-agent
python -m venv venv
```

Activar el entorno virtual:

```bash
# Windows
venv\Scripts\activate

# Linux / macOS / EC2
source venv/bin/activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

La interfaz web no requiere instalar nada adicional (no usa Node.js, npm ni
frameworks de frontend).

## 7. Configuración

Copiar el archivo de ejemplo y ajustar los valores según el entorno:

```bash
cp .env.example .env
```

Variables disponibles:

| Variable            | Descripción                                              | Valor por defecto |
|---------------------|-----------------------------------------------------------|--------------------|
| MODEL_PROVIDER      | `local` (heurístico) o `bedrock`                          | `local`            |
| AWS_REGION          | Región de AWS (solo si `MODEL_PROVIDER=bedrock`)           | `us-east-1`        |
| BEDROCK_MODEL_ID    | Id del modelo de Bedrock a usar                            | Claude Haiku       |
| LOG_LEVEL           | Nivel de logging                                           | `INFO`             |
| DATA_DIR            | Carpeta donde se guarda `complaints.jsonl`                 | `./data`           |
| PERSIST_COMPLAINTS  | Activa/desactiva el registro en `complaints.jsonl`         | `true`             |

**Nunca** se deben subir credenciales reales al repositorio. El archivo
`.env` está incluido en `.gitignore`.

## 8. Ejecución local

```bash
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Una vez iniciado:

| Recurso                  | URL                              |
|--------------------------|----------------------------------|
| Interfaz web             | http://localhost:8000/           |
| Documentación (Swagger)  | http://localhost:8000/docs       |
| Health check             | http://localhost:8000/health     |

### Interfaz web

En `http://localhost:8000/` se muestra un formulario con ID de queja, ID del
cliente, canal (Web, App, Correo, Teléfono) y el mensaje. Al pulsar
**Analizar queja**, la página envía la solicitud a `POST /agent/complaint` y
muestra categoría, severidad, sentimiento, prioridad, confianza, resumen,
acción recomendada y si se requiere revisión humana.

- La interfaz solo **consume la API existente**; la clasificación y la
  validación (Pydantic) siguen ocurriendo en el backend.
- Usa rutas relativas (`fetch("/agent/complaint")`), por lo que funciona igual
  en `localhost` y en la IP pública de EC2 sin cambiar nada.
- No contiene credenciales, API keys ni secretos.

### Probar la API directamente

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/agent/complaint \
  -H "Content-Type: application/json" \
  -d @examples/complaint_input.json
```

Documentación interactiva (Swagger), para la demostración técnica de la API:
`http://localhost:8000/docs`

## 9. Ejemplos de entrada y salida

Ver [examples/complaint_input.json](examples/complaint_input.json) y
[examples/complaint_output.json](examples/complaint_output.json).

Entrada:
```json
{
  "complaint_id": "CMP-001",
  "customer_id": "CUS-1001",
  "channel": "web",
  "message": "Mi pedido lleva tres días de retraso y nadie me da una solución."
}
```

Salida:
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

Más ejemplos de solicitudes en [data/examples.json](data/examples.json).
El detalle de todos los endpoints está en [docs/api.md](docs/api.md).

## 10. Pruebas

```bash
python -m pytest -v
```

Casos cubiertos (`tests/test_agent.py`, `tests/test_classifier.py` y
`tests/test_frontend.py`):

1. Queja de entrega
2. Queja de facturación
3. Queja de producto
4. Mensaje que no es una queja
5. Mensaje ambiguo
6. Queja crítica
7. JSON incompleto (falta un campo obligatorio) → HTTP 400
8. Mensaje vacío → HTTP 400
9. Clasificación con baja confianza → `needs_human_review = true`
10. Interfaz web: `/` sirve la página, los archivos estáticos están
    disponibles y el script usa rutas relativas
11. Swagger (`/docs`) y `/health` siguen funcionando
12. La estructura de la respuesta de `POST /agent/complaint` no cambió

## 11. Despliegue en AWS EC2

1. **Lanzar la instancia**
   - Crear una instancia EC2 (por ejemplo, Amazon Linux 2023, tipo `t3.micro`
     o `t2.micro` para uso académico).
   - Abrir en el Security Group el puerto `22` (SSH) desde tu IP y el puerto
     `8000` (o `80` si se usa un proxy) para el tráfico de la API.

2. **Conectarse e instalar dependencias**
   ```bash
   ssh -i mi-llave.pem ec2-user@<IP-PUBLICA>
   sudo yum install -y python3.11 git
   ```

3. **Clonar el proyecto y preparar el entorno**
   ```bash
   git clone <url-del-repositorio>
   cd complaint-agent
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env
   # Editar .env con los valores reales de la instancia (sin credenciales en el repo)
   ```

4. **Ejecutar el servicio**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```
   Para mantenerlo activo tras cerrar la sesión SSH, usar `systemd`, `tmux`
   o `nohup`. Ejemplo simple con `nohup`:
   ```bash
   nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
   ```

5. **(Opcional) Usar Amazon Bedrock como modelo de IA**
   - Asignar a la instancia EC2 un rol de IAM con permiso
     `bedrock:InvokeModel` sobre el modelo elegido.
   - En `.env`, definir `MODEL_PROVIDER=bedrock` y `BEDROCK_MODEL_ID` con el
     identificador del modelo ligero a usar (por ejemplo, Claude Haiku).
   - No es necesario cambiar código: `classifier.py` selecciona el modelo
     automáticamente según `MODEL_PROVIDER`.

6. **(Opcional) Enviar logs a Amazon CloudWatch**
   - Instalar el agente de CloudWatch (`amazon-cloudwatch-agent`) en la
     instancia.
   - Configurarlo para recolectar la salida estándar del proceso de Uvicorn
     (o el archivo `app.log` si se usa `nohup`) y enviarla a un log group,
     por ejemplo `complaint-agent-ai`.
   - Los logs generados por el agente ya están en formato JSON y **no**
     incluyen el mensaje original del cliente ni el `customer_id`.

7. **Probar el despliegue**
   ```bash
   curl http://<IP-PUBLICA>:8000/health
   ```
   Interfaz web: `http://<IP-PUBLICA>:8000/` · Swagger:
   `http://<IP-PUBLICA>:8000/docs`. No hay que modificar la interfaz para EC2,
   porque usa rutas relativas.

## 12. Seguridad

- No se almacenan contraseñas ni API keys en el repositorio; se usan
  variables de entorno (`.env`, excluido de Git mediante `.gitignore`).
- `.env.example` no contiene valores reales, solo la lista de variables
  necesarias.
- Los registros (`data/complaints.jsonl` y los logs de la aplicación) no
  incluyen el texto del mensaje del cliente ni el `customer_id`, solo
  metadatos de clasificación (categoría, severidad, prioridad, etc.).
- El modelo de IA **solo clasifica y recomienda**; nunca ejecuta acciones
  externas (no envía correos, no modifica pedidos, no realiza reembolsos).

## 13. Alcance y limitaciones

Este es un proyecto académico. El modelo de IA por defecto es un
clasificador heurístico ligero basado en palabras clave, pensado para
ejecutarse sin dependencias pesadas en una instancia EC2 pequeña y para
facilitar la explicación del funcionamiento interno en una presentación. La
capa `classifier.py` está diseñada para poder integrarse con un modelo real
de Amazon Bedrock sin modificar el resto de la aplicación.
