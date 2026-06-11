import pytest
from tasks import fatorial, somar

# ==========================================
# TESTES DE SOMA
# ==========================================
def test_calcular_soma():
    resultado = somar.apply(args=[3, 5]).get()
    assert resultado == 8

# ==========================================
# TESTES DE FATORIAL
# ==========================================
def test_calcular_fatorial():
    resultado = fatorial.apply(args=[5]).get()
    assert resultado == 120

def test_calcular_fatorial_zero():
    """Caso de borda: garante que o fatorial de 0 é 1"""
    resultado = fatorial.apply(args=[0]).get()
    assert resultado == 1

def test_calcular_fatorial_negativo():
    """Garante que a task levanta o erro correto ao receber número negativo"""
    with pytest.raises(ValueError, match="Número negativo não permitido"):
        fatorial.apply(args=[-1]).get()