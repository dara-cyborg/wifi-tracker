import asyncio
import importlib
import os

import httpx
import pytest


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "password")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("BAKONG_DEVELOPER_TOKEN", "token")
    monkeypatch.setenv("BAKONG_MERCHANT_ACCOUNT_ID", "account")
    monkeypatch.setenv("BAKONG_MERCHANT_NAME", "merchant")
    monkeypatch.setenv("BAKONG_MERCHANT_CITY", "Phnom Penh")
    monkeypatch.setenv("ENVIRONMENT", "production")

    import backend.main as main_module
    import backend.routes as routes_module

    importlib.reload(routes_module)
    importlib.reload(main_module)
    return main_module.app


def request(app, method, path, **kwargs):
    async def run_request():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(run_request())


def test_admin_auth_check_returns_boolean_when_unauthenticated(app):
    response = request(app, "GET", "/admin/auth/check")
    assert response.status_code == 200
    assert response.json() == {"authenticated": False}


def test_admin_root_redirects_to_login_when_unauthenticated(app):
    response = request(app, "GET", "/admin")
    assert response.status_code == 302
    assert response.headers["location"].endswith("/admin/login")


def test_removed_admin_pages_are_not_available(app):
    assert request(app, "GET", "/admin/add").status_code == 404
    assert request(app, "GET", "/admin/edit").status_code == 404


def test_customer_routes_require_authentication(app):
    qr_response = request(app, "POST", "/customer/payment/generate-qr/1")
    assert qr_response.status_code == 401

    verify_response = request(app, "POST", "/customer/payment/verify", json={})
    assert verify_response.status_code == 401

    pricing_response = request(app, "GET", "/customer/pricing/1")
    assert pricing_response.status_code == 401


def test_openapi_docs_disabled_in_production(app):
    assert request(app, "GET", "/docs").status_code == 404
    assert request(app, "GET", "/openapi.json").status_code == 404
