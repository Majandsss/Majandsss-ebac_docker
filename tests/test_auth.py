from fastapi.testclient import TestClient
from main import app
import os
import pytest

client = TestClient(app)

os.environ["MEU_USUARIO"] = "admin"
os.environ["MINHA_SENHA"] = "admin"

@pytest.fixture(autouse=True)
def mock_redis(mocker):
    mock_redis_client = mocker.patch("main.redis_client", autospec=True)
    mock_redis_client.get.return_value = None

def test_autenticacao_usuario_sucesso():
    response = client.get("/livros", auth=("admin", "admin"))
    assert response.status_code == 200

def test_autenticacao_usuario_falha():
    response = client.get("/livros", auth=("usuario_incorreto", "admin"))
    assert response.status_code == 401
    assert response.json()["detail"] == "Usuário não autorizado! Credenciais inválidas!"

def test_autenticacao_senha_falha():
    response = client.get("/livros", auth=("admin", "senha_incorreta"))
    assert response.status_code == 401
    assert response.json()["detail"] == "Usuário não autorizado! Credenciais inválidas!"