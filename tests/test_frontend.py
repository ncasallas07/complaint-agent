"""Pruebas de la interfaz web y de que la API existente sigue intacta."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

EXPECTED_RESPONSE_KEYS = {
    "complaint_id",
    "is_complaint",
    "category",
    "severity",
    "sentiment",
    "priority",
    "summary",
    "recommended_action",
    "confidence",
    "needs_human_review",
}


@pytest.fixture(autouse=True)
def no_persist(monkeypatch):
    """Evita escribir en data/complaints.jsonl durante las pruebas."""
    monkeypatch.setenv("PERSIST_COMPLAINTS", "false")


def test_raiz_sirve_la_interfaz_web():
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "ComplaintAgent AI" in response.text
    assert "Analizar queja" in response.text


@pytest.mark.parametrize("path, content_type", [
    ("/static/style.css", "text/css"),
    ("/static/script.js", "javascript"),
])
def test_archivos_estaticos_disponibles(path, content_type):
    response = client.get(path)
    assert response.status_code == 200
    assert content_type in response.headers["content-type"]


def test_script_usa_ruta_relativa_y_no_localhost():
    script = client.get("/static/script.js").text
    assert '"/agent/complaint"' in script
    # Ninguna URL absoluta: así funciona igual en localhost y en la IP de EC2.
    assert "http://" not in script
    assert "https://" not in script
    assert "fetch(API_URL" in script


def test_select_de_canal_usa_valores_de_la_api():
    html = client.get("/").text
    for value in ("web", "app", "email", "phone"):
        assert f'value="{value}"' in html


def test_swagger_sigue_disponible():
    assert client.get("/docs").status_code == 200
    schema = client.get("/openapi.json").json()
    assert "/agent/complaint" in schema["paths"]
    assert "/health" in schema["paths"]
    # La ruta de la interfaz no se mezcla con la documentación de la API.
    assert "/" not in schema["paths"]


def test_health_sigue_funcionando():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_estructura_de_respuesta_no_cambio():
    response = client.post("/agent/complaint", json={
        "complaint_id": "CMP-001",
        "customer_id": "CUS-1001",
        "channel": "web",
        "message": "Mi pedido lleva tres días de retraso y nadie me da una solución.",
    })
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == EXPECTED_RESPONSE_KEYS
    assert body["category"] == "entrega"
    assert body["severity"] == "alta"
    assert body["priority"] == "urgente"
    assert body["sentiment"] == "negativo"


def test_validacion_del_backend_sigue_activa():
    response = client.post("/agent/complaint", json={
        "complaint_id": "CMP-010",
        "customer_id": "CUS-1010",
        "channel": "web",
        "message": "",
    })
    assert response.status_code == 400
    assert response.json()["error"] == "validation_error"
