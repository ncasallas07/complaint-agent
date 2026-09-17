"""Pruebas de integración del endpoint POST /agent/complaint."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_persist(monkeypatch):
    """Evita escribir en data/complaints.jsonl durante las pruebas."""
    monkeypatch.setenv("PERSIST_COMPLAINTS", "false")


def _post(payload):
    return client.post("/agent/complaint", json=payload)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_1_queja_de_entrega():
    response = _post({
        "complaint_id": "CMP-001",
        "customer_id": "CUS-1001",
        "channel": "web",
        "message": "Mi pedido lleva tres días de retraso y nadie me da una solución.",
    })
    body = response.json()
    assert response.status_code == 200
    assert body["is_complaint"] is True
    assert body["category"] == "entrega"
    assert body["priority"] in {"media", "urgente"}


def test_2_queja_de_facturacion():
    response = _post({
        "complaint_id": "CMP-002",
        "customer_id": "CUS-1002",
        "channel": "app",
        "message": "Me cobraron dos veces la misma factura y necesito el reembolso de mi dinero.",
    })
    body = response.json()
    assert response.status_code == 200
    assert body["category"] == "facturacion"
    assert body["is_complaint"] is True


def test_3_queja_de_producto():
    response = _post({
        "complaint_id": "CMP-003",
        "customer_id": "CUS-1003",
        "channel": "email",
        "message": "El producto llegó dañado y no funciona, es de muy mala calidad.",
    })
    body = response.json()
    assert response.status_code == 200
    assert body["category"] == "producto"
    assert body["is_complaint"] is True


def test_4_mensaje_que_no_es_queja():
    response = _post({
        "complaint_id": "CMP-004",
        "customer_id": "CUS-1004",
        "channel": "web",
        "message": "Quisiera saber el horario de atención de la tienda los fines de semana.",
    })
    body = response.json()
    assert response.status_code == 200
    assert body["is_complaint"] is False
    assert body["priority"] == "baja"


def test_5_mensaje_ambiguo():
    response = _post({
        "complaint_id": "CMP-005",
        "customer_id": "CUS-1005",
        "channel": "phone",
        "message": "No sé, tal vez, no estoy seguro de lo que pasó con mi pedido.",
    })
    body = response.json()
    assert response.status_code == 200
    assert body["needs_human_review"] is True


def test_6_queja_critica():
    response = _post({
        "complaint_id": "CMP-006",
        "customer_id": "CUS-1006",
        "channel": "email",
        "message": "Esto es una estafa, voy a contactar a mi abogado y poner una demanda.",
    })
    body = response.json()
    assert response.status_code == 200
    assert body["severity"] == "critica"
    assert body["needs_human_review"] is True
    assert body["priority"] == "urgente"


def test_7_json_incompleto_devuelve_400():
    response = client.post("/agent/complaint", json={
        "complaint_id": "CMP-007",
        "channel": "web",
        # falta "message"
    })
    body = response.json()
    assert response.status_code == 400
    assert body["error"] == "validation_error"
    assert any(detail["field"] == "message" for detail in body["details"])


def test_8_mensaje_vacio_devuelve_400():
    response = _post({
        "complaint_id": "CMP-008",
        "customer_id": "CUS-1008",
        "channel": "web",
        "message": "   ",
    })
    assert response.status_code == 400


def test_9_baja_confianza_requiere_revision_humana():
    response = _post({
        "complaint_id": "CMP-009",
        "customer_id": "CUS-1009",
        "channel": "web",
        "message": "Hola, algo pasó y no sé bien qué fue.",
    })
    body = response.json()
    assert response.status_code == 200
    assert body["confidence"] < 0.80
    assert body["needs_human_review"] is True
