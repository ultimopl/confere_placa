import os
import shutil
import tempfile
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient

from web.main import app
from web.auth import init_default_admin, load_users, _sessions
from web.repository import repository
from web.config import set_active_csv_path
from web.chat_manager import chat_manager

@pytest.fixture(autouse=True)
def setup_test_env():
    # Use a temporary directory for test data
    test_dir = tempfile.mkdtemp(prefix="confere_test_")
    test_csv = os.path.join(test_dir, "test_plates.csv")

    # Create dummy initial CSV
    with open(test_csv, "w", encoding="utf-8") as f:
        f.write("ABC1234;Veículo Teste 1;autorizado;2026-01-01T10:00:00;\n")
        f.write("XYZ9876;Veículo Bloqueado;não autorizado;2026-01-01T10:00:00;\n")

    repository.load(test_csv)
    set_active_csv_path(test_csv)
    init_default_admin()
    _sessions.clear()
    chat_manager.clear_history()
    chat_manager.active_connections.clear()

    yield {
        "test_dir": test_dir,
        "test_csv": test_csv,
    }

    # Teardown
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


@pytest.fixture
def client():
    return TestClient(app)


def login_helper(client, username, password):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200
    token = res.json()["token"]
    return token


# ==================== AUTH & RBAC TESTS ====================

def test_login_success_and_logout(client):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "admin"

    # Test me endpoint with cookie
    me_res = client.get("/api/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["user"]["username"] == "admin"

    # Test logout
    logout_res = client.post("/api/auth/logout")
    assert logout_res.status_code == 200

    # After logout, me should be 401
    me_res_after = client.get("/api/auth/me")
    assert me_res_after.status_code == 401


def test_login_invalid_credentials(client):
    res = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert res.status_code == 401


def test_rbac_operator_restrictions(client):
    # Admin creates an operator
    login_helper(client, "admin", "admin123")
    create_res = client.post("/api/auth/users", json={
        "username": "operador1",
        "name": "Agente Teste",
        "password": "senha_operador",
        "role": "operador"
    })
    assert create_res.status_code == 200

    # Logout admin
    client.post("/api/auth/logout")

    # Login as operator
    login_helper(client, "operador1", "senha_operador")

    # Operator CAN search plates
    search_res = client.get("/api/plates?q=ABC")
    assert search_res.status_code == 200
    assert search_res.json()["count"] == 1

    # Operator CANNOT add plate (403)
    add_res = client.post("/api/plates", json={
        "placa": "NEW1234",
        "detalhes": "Tentativa",
        "status": "autorizado"
    })
    assert add_res.status_code == 403

    # Operator CANNOT edit plate (403)
    edit_res = client.put("/api/plates/ABC1234", json={
        "detalhes": "Tentativa Edit",
        "status": "autorizado"
    })
    assert edit_res.status_code == 403

    # Operator CANNOT delete plate (403)
    del_res = client.delete("/api/plates/ABC1234")
    assert del_res.status_code == 403

    # Operator CANNOT list users (403)
    users_res = client.get("/api/auth/users")
    assert users_res.status_code == 403


# ==================== PLATES & SEARCH TESTS ====================

def test_add_and_search_plate(client):
    login_helper(client, "admin", "admin123")

    # Add Mercosul plate
    add_res = client.post("/api/plates", json={
        "placa": "BRA2E19",
        "detalhes": "Carro Diretoria",
        "status": "autorizado"
    })
    assert add_res.status_code == 200
    assert add_res.json()["plate"]["placa"] == "BRA2E19"

    # Search query
    res = client.get("/api/plates?q=BRA2")
    assert res.status_code == 200
    assert res.json()["count"] == 1
    assert res.json()["results"][0]["placa"] == "BRA2E19"


def test_invalid_plate_format(client):
    login_helper(client, "admin", "admin123")

    # Invalid plate format
    res = client.post("/api/plates", json={
        "placa": "INVALIDA999",
        "detalhes": "Invalida",
        "status": "autorizado"
    })
    assert res.status_code == 400
    assert "Formato de placa inválido" in res.json()["detail"]


def test_temporary_plates_active_and_expired(client):
    login_helper(client, "admin", "admin123")

    # 1. Add active temporary plate (+4 hours)
    res_active = client.post("/api/plates", json={
        "placa": "TMP1A11",
        "detalhes": "Visitante Ativo",
        "status": "autorizado_temp",
        "duration_hours": 4
    })
    assert res_active.status_code == 200
    assert res_active.json()["plate"]["expired"] is False
    assert res_active.json()["plate"]["is_authorized"] is True

    # 2. Add expired temporary plate (expired yesterday)
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M")
    res_expired = client.post("/api/plates", json={
        "placa": "TMP2B22",
        "detalhes": "Visitante Vencido",
        "status": "autorizado_temp",
        "expires_at": yesterday
    })
    assert res_expired.status_code == 200
    assert res_expired.json()["plate"]["expired"] is True
    assert res_expired.json()["plate"]["is_authorized"] is False

    # 3. Test filter temp_filter=active
    search_active = client.get("/api/plates?temp_filter=active")
    assert search_active.status_code == 200
    placas = [p["placa"] for p in search_active.json()["results"]]
    assert "TMP1A11" in placas
    assert "TMP2B22" not in placas

    # 4. Test filter temp_filter=expired
    search_exp = client.get("/api/plates?temp_filter=expired")
    assert search_exp.status_code == 200
    placas_exp = [p["placa"] for p in search_exp.json()["results"]]
    assert "TMP2B22" in placas_exp
    assert "TMP1A11" not in placas_exp


def test_soft_delete_plate(client):
    login_helper(client, "admin", "admin123")

    # Verify plate exists
    get_res = client.get("/api/plates/ABC1234")
    assert get_res.status_code == 200

    # Delete plate
    del_res = client.delete("/api/plates/ABC1234")
    assert del_res.status_code == 200

    # Search should no longer return it
    search_res = client.get("/api/plates?q=ABC1234")
    assert search_res.status_code == 200
    assert search_res.json()["count"] == 0

    # Direct get should return 404
    get_after = client.get("/api/plates/ABC1234")
    assert get_after.status_code == 404


def test_history_and_stats(client):
    login_helper(client, "admin", "admin123")

    # Search queries create history
    client.get("/api/plates?q=BUSCA1")
    client.get("/api/plates?q=BUSCA2")

    hist_res = client.get("/api/plates/history")
    assert hist_res.status_code == 200
    queries = [h["query"] for h in hist_res.json()["history"]]
    assert "BUSCA2" in queries
    assert "BUSCA1" in queries

    # Clear history
    clear_res = client.delete("/api/plates/history")
    assert clear_res.status_code == 200
    hist_after = client.get("/api/plates/history")
    assert len(hist_after.json()["history"]) == 0

    # Stats endpoint
    stats_res = client.get("/api/config")
    assert stats_res.status_code == 200
    assert "total" in stats_res.json()["stats"]


def test_index_html_served(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Confere Placa" in res.text
    assert "modal-login" in res.text


def test_cor_and_modelo_support_and_backward_compatibility(client, setup_test_env):
    login_helper(client, "admin", "admin123")

    # 1. Existing plates from setup_test_env (legacy 4 columns without cor/modelo) load seamlessly
    res_legacy = client.get("/api/plates/ABC1234")
    assert res_legacy.status_code == 200
    plate_legacy = res_legacy.json()["plate"]
    assert plate_legacy["cor"] == ""
    assert plate_legacy["modelo"] == ""

    # 2. Add plate with modelo and cor
    add_res = client.post("/api/plates", json={
        "placa": "CIV1C99",
        "detalhes": "Diretor Comercial",
        "status": "autorizado",
        "modelo": "Honda Civic",
        "cor": "Prata Metálico",
    })
    assert add_res.status_code == 200
    plate_new = add_res.json()["plate"]
    assert plate_new["modelo"] == "Honda Civic"
    assert plate_new["cor"] == "Prata Metálico"

    # 3. Search by modelo
    search_modelo = client.get("/api/plates?q=Civic")
    assert search_modelo.status_code == 200
    assert search_modelo.json()["count"] == 1
    assert search_modelo.json()["results"][0]["placa"] == "CIV1C99"

    # 4. Search by cor
    search_cor = client.get("/api/plates?q=Prata")
    assert search_cor.status_code == 200
    assert search_cor.json()["count"] == 1
    assert search_cor.json()["results"][0]["placa"] == "CIV1C99"

    # 5. Edit modelo and cor
    edit_res = client.put("/api/plates/CIV1C99", json={
        "detalhes": "Diretor Comercial (Novo Veículo)",
        "status": "autorizado",
        "modelo": "Toyota Corolla",
        "cor": "Preto",
    })
    assert edit_res.status_code == 200
    plate_updated = edit_res.json()["plate"]
    assert plate_updated["modelo"] == "Toyota Corolla"
    assert plate_updated["cor"] == "Preto"

    # 6. Check CSV persistence: read raw file
    with open(setup_test_env["test_csv"], "r", encoding="utf-8") as f:
        content = f.read()
    assert "CIV1C99;Diretor Comercial (Novo Veículo);autorizado;" in content
    assert ";Preto;Toyota Corolla" in content


# ==================== CHAT & REALTIME TESTS ====================

def test_chat_rest_api_and_permissions(client):
    # Unauthenticated should fail (401)
    res_unauth = client.get("/api/chat/messages")
    assert res_unauth.status_code == 401

    token_admin = login_helper(client, "admin", "admin123")

    # Send message via REST
    send_res = client.post("/api/chat/messages", json={"text": "Olá portaria!"})
    assert send_res.status_code == 200
    msg = send_res.json()["message"]
    assert msg["text"] == "Olá portaria!"
    assert msg["username"] == "admin"
    assert msg["role"] == "admin"

    # Get message history
    get_res = client.get("/api/chat/messages")
    assert get_res.status_code == 200
    messages = get_res.json()["messages"]
    assert len(messages) == 1
    assert messages[0]["text"] == "Olá portaria!"

    # Operator sends message
    client.post("/api/auth/users", json={
        "username": "operador_joao",
        "name": "João Agente",
        "password": "senha",
        "role": "operador"
    })
    client.post("/api/auth/logout")

    token_op = login_helper(client, "operador_joao", "senha")
    send_op = client.post("/api/chat/messages", json={"text": "Copiado, administrativo!"})
    assert send_op.status_code == 200

    # Operator cannot clear chat history (403)
    clear_op = client.delete("/api/chat/messages")
    assert clear_op.status_code == 403

    # Admin clears chat history
    client.post("/api/auth/logout")
    login_helper(client, "admin", "admin123")
    clear_admin = client.delete("/api/chat/messages")
    assert clear_admin.status_code == 200

    # History is now empty
    get_res_empty = client.get("/api/chat/messages")
    assert len(get_res_empty.json()["messages"]) == 0


def test_chat_websocket_flow_and_broadcast(client):
    token = login_helper(client, "admin", "admin123")

    with client.websocket_connect(f"/api/chat/ws?token={token}") as ws:
        # Upon connecting, server broadcasts users_update
        first_msg = ws.receive_json()
        assert first_msg["type"] == "users_update"
        assert first_msg["count"] >= 1
        usernames = [u["username"] for u in first_msg["online_users"]]
        assert "admin" in usernames

        # Send chat message over websocket
        ws.send_json({"type": "chat_message", "text": "Mensagem via WebSocket teste!"})

        # Receive broadcasted message
        chat_msg = ws.receive_json()
        assert chat_msg["type"] == "chat_message"
        assert chat_msg["text"] == "Mensagem via WebSocket teste!"
        assert chat_msg["username"] == "admin"

        # Test ping/pong
        ws.send_json({"type": "ping"})
        pong_msg = ws.receive_json()
        assert pong_msg["type"] == "pong"


def test_new_plate_broadcast_alert(client):
    token = login_helper(client, "admin", "admin123")

    with client.websocket_connect(f"/api/chat/ws?token={token}") as ws:
        # Initial user list
        init_ws = ws.receive_json()
        assert init_ws["type"] == "users_update"

        # Register a new plate via REST API
        add_res = client.post("/api/plates", json={
            "placa": "ALT1B23",
            "detalhes": "Visitante Especial",
            "status": "autorizado",
            "modelo": "Jeep Compass",
            "cor": "Azul"
        })
        assert add_res.status_code == 200

        # Websocket should receive the new_plate_alert broadcast
        alert_msg = ws.receive_json()
        assert alert_msg["type"] == "new_plate_alert"
        assert alert_msg["plate"]["placa"] == "ALT1B23"
        assert alert_msg["plate"]["modelo"] == "Jeep Compass"
        assert alert_msg["created_by"] == "admin"
        assert alert_msg["loud_alert"] is False

        # Register another plate with loud_alert=True
        add_res_loud = client.post("/api/plates", json={
            "placa": "LOD9X99",
            "detalhes": "Alerta Urgente",
            "status": "autorizado",
            "modelo": "Caminhão Baú",
            "cor": "Branco",
            "loud_alert": True
        })
        assert add_res_loud.status_code == 200

        alert_msg_loud = ws.receive_json()
        assert alert_msg_loud["type"] == "new_plate_alert"
        assert alert_msg_loud["plate"]["placa"] == "LOD9X99"
        assert alert_msg_loud["loud_alert"] is True

