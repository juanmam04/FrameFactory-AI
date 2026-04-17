"""Reglas de tokens: administradores exentos."""
from types import SimpleNamespace

from src.saas_platform.billing import deduct_tokens_after_success, user_is_admin, user_may_generate


def test_user_is_admin():
    assert user_is_admin(SimpleNamespace(role="admin")) is True
    assert user_is_admin(SimpleNamespace(role="user")) is False


def test_user_may_generate_admin_sin_saldo():
    u = SimpleNamespace(role="admin", is_active=True)
    ok, msg = user_may_generate(u, 0)
    assert ok is True
    assert msg == ""


def test_user_may_generate_usuario_sin_sub():
    u = SimpleNamespace(role="user", is_active=True, subscription=None)
    ok, msg = user_may_generate(u, 99999)
    assert ok is False
    assert "suscripción" in msg.lower()


def test_user_may_generate_usuario_sin_tokens():
    sub = SimpleNamespace(status="active")
    u = SimpleNamespace(role="user", is_active=True, subscription=sub)
    ok, msg = user_may_generate(u, 10)
    assert ok is False
    assert "insuficiente" in msg.lower() or "tokens" in msg.lower()


def test_deduct_tokens_admin_no_op(monkeypatch):
    class DummyUser:
        role = "admin"
        id = 1

    class DummySession:
        def add(self, *a, **k):
            raise AssertionError("no debe escribir transacciones para admin")

    ok, reason = deduct_tokens_after_success(DummySession(), DummyUser(), job_id=9)
    assert ok is True
    assert reason == "admin_exempt"
