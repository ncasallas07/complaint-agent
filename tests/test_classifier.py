"""Pruebas unitarias de la capa de modelo (app/classifier.py)."""
from app.classifier import LocalHeuristicModel

model = LocalHeuristicModel()


def test_queja_de_entrega():
    result = model.classify("Mi pedido lleva tres días de retraso y nadie me da una solución.")
    assert result["is_complaint"] is True
    assert result["category"] == "entrega"


def test_queja_de_facturacion():
    result = model.classify("Me cobraron dos veces la misma factura y necesito el reembolso de mi dinero.")
    assert result["is_complaint"] is True
    assert result["category"] == "facturacion"


def test_queja_de_producto():
    result = model.classify("El producto llegó dañado y no funciona, es de muy mala calidad.")
    assert result["is_complaint"] is True
    assert result["category"] == "producto"


def test_mensaje_que_no_es_queja():
    result = model.classify("Quisiera saber el horario de atención de la tienda los fines de semana.")
    assert result["is_complaint"] is False
    assert result["category"] == "otro"


def test_queja_critica():
    result = model.classify("Esto es una estafa, voy a contactar a mi abogado y poner una demanda.")
    assert result["severity"] == "critica"


def test_mensaje_ambiguo_tiene_baja_confianza():
    result = model.classify("No sé, tal vez, no estoy seguro de lo que pasó.")
    assert result["confidence"] < 0.80


def test_queja_con_problema_concreto_es_negativa():
    # Sin adjetivos emocionales, pero describe retraso, daño y urgencia.
    result = model.classify(
        "Mi pedido llegó con 5 días de retraso y el producto vino dañado. "
        "Necesito una solución urgente."
    )
    assert result["is_complaint"] is True
    assert result["sentiment"] == "negativo"


def test_mensaje_positivo_sigue_siendo_positivo():
    result = model.classify("Gracias, el pedido llegó a tiempo y estoy muy contento.")
    assert result["sentiment"] == "positivo"
