import base64
import re
import sqlite3
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

import app as app_module
from app import create_app


def make_app(tmp_path):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only-secret",
        "DATABASE": str(tmp_path / "test.sqlite3"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })


def png_bytes():
    buffer = BytesIO()
    Image.new("RGB", (3, 3), "orange").save(buffer, format="PNG")
    return buffer.getvalue()


def csrf(client, path):
    response = client.get(path)
    assert response.status_code == 200
    match = re.search(
        r'name="_csrf_token" value="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match, "form must contain CSRF token"
    return match.group(1)


def create_admin(client):
    token = csrf(client, "/configurar")
    response = client.post("/configurar", data={
        "_csrf_token": token,
        "username": "admincentral",
        "password": "senha-forte-de-teste-123",
        "confirmation": "senha-forte-de-teste-123",
    })
    assert response.status_code == 302


def create_product(app, client, name="Produto de teste"):
    token = csrf(client, "/produtos/novo")
    response = client.post("/produtos/novo", data={
        "_csrf_token": token,
        "name": name,
        "category": "Teste",
        "price": "119,90",
        "affiliate_link": "https://shopee.com.br/produto-teste",
        "commission": "8",
        "photos": [(BytesIO(png_bytes()), "produto.png")],
    }, content_type="multipart/form-data")
    assert response.status_code == 302
    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        return conn.execute(
            "SELECT id FROM products WHERE name=?", (name,)
        ).fetchone()[0]
    finally:
        conn.close()


def test_first_created_user_is_administrator(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    create_admin(client)

    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        assert conn.execute(
            "SELECT is_admin FROM users WHERE username='admincentral'"
        ).fetchone()[0] == 1
    finally:
        conn.close()

    response = client.get("/usuarios")
    assert response.status_code == 200


def test_invalid_shopee_link_renders_form_without_database_name_error(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    create_admin(client)

    token = csrf(client, "/produtos/novo")
    response = client.post("/produtos/importar-link", data={
        "_csrf_token": token,
        "affiliate_link": "https://shopee.com.br.attacker.invalid/item",
    })

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Cole um link HTTPS válido da Shopee" in html
    assert 'name="name"' in html


def test_shopee_link_import_uses_structured_data_and_does_not_guess_commission(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    client = app.test_client()
    create_admin(client)

    html = (
        '<meta property="og:title" content="Tênis de corrida teste | Shopee">'
        '<meta property="og:description" content="Descrição cadastrada do produto">'
        '<script type="application/ld+json">'
        '{"@type":"Product","name":"Tênis de corrida teste",'
        '"category":"Corrida","offers":{"price":"119.90"}}'
        '</script>'
    ).encode("utf-8")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def geturl(self):
            return "https://shopee.com.br/product/123"

        def read(self, size=-1):
            return html[:size] if size >= 0 else html

    class FakeOpener:
        def open(self, request, timeout):
            assert timeout == 15
            return FakeResponse()

    monkeypatch.setattr(
        app_module.urllib.request,
        "build_opener",
        lambda handler: FakeOpener(),
    )

    token = csrf(client, "/produtos/novo")
    response = client.post("/produtos/importar-link", data={
        "_csrf_token": token,
        "affiliate_link": "https://shopee.com.br/product/123",
    })
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'value="Tênis de corrida teste"' in page
    assert 'value="119,90"' in page
    assert "Descrição cadastrada do produto" in page
    assert 'name="commission"' in page
    assert "name=\"commission\" inputmode=\"decimal\" value=\"\"" in page

    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0
    finally:
        conn.close()


def test_shopee_redirect_handler_blocks_non_shopee_destination(tmp_path, monkeypatch):
    import urllib.error

    app = make_app(tmp_path)
    client = app.test_client()
    create_admin(client)
    rejected = {"value": False}

    class FakeOpener:
        def __init__(self, handler):
            self.handler = handler

        def open(self, request, timeout):
            with pytest.raises(urllib.error.URLError):
                self.handler.redirect_request(
                    request, None, 302, "Found", {},
                    "http://127.0.0.1:5000/private",
                )
            rejected["value"] = True
            raise urllib.error.URLError("blocked")

    monkeypatch.setattr(
        app_module.urllib.request,
        "build_opener",
        lambda handler: FakeOpener(handler),
    )

    token = csrf(client, "/produtos/novo")
    response = client.post("/produtos/importar-link", data={
        "_csrf_token": token,
        "affiliate_link": "https://shopee.com.br/product/123",
    })

    assert response.status_code == 200
    assert rejected["value"] is True
    assert "Não consegui ler os dados desta página da Shopee" in response.get_data(as_text=True)


@pytest.mark.parametrize("field,value", [
    ("price", "NaN"),
    ("price", "Infinity"),
    ("price", "-Infinity"),
    ("commission", "NaN"),
    ("commission", "Infinity"),
])
def test_catalog_rejects_non_finite_numeric_values(tmp_path, field, value):
    app = make_app(tmp_path)
    client = app.test_client()
    create_admin(client)

    token = csrf(client, "/produtos/novo")
    data = {
        "_csrf_token": token,
        "name": "Produto numérico inválido",
        "category": "Teste",
        "price": "10,00",
        "commission": "8",
        "affiliate_link": "https://shopee.com.br/produto-teste",
    }
    data[field] = value
    response = client.post(
        "/produtos/novo",
        data=data,
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert "Informe um preço positivo e uma comissão entre 0 e 100%" in response.get_data(as_text=True)
    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0
    finally:
        conn.close()


def test_uploaded_images_are_private_and_invalid_files_are_rejected(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    create_admin(client)

    token = csrf(client, "/produtos/novo")
    invalid = client.post("/produtos/novo", data={
        "_csrf_token": token,
        "name": "Arquivo não é imagem",
        "price": "10,00",
        "photos": (BytesIO(b"isso-nao-e-imagem"), "foto.jpg"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert invalid.status_code == 200
    assert "não é uma imagem válida" in invalid.get_data(as_text=True)

    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0
    finally:
        conn.close()

    token = csrf(client, "/produtos/novo")
    saved = client.post("/produtos/novo", data={
        "_csrf_token": token,
        "name": "Produto com foto privada",
        "price": "19,90",
        "photos": (BytesIO(png_bytes()), "foto.png"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert saved.status_code == 200

    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        filename = conn.execute(
            "SELECT image_filename FROM products WHERE name=?",
            ("Produto com foto privada",),
        ).fetchone()[0]
    finally:
        conn.close()

    assert (Path(app.config["UPLOAD_FOLDER"]) / filename).is_file()
    assert client.get(f"/uploads/{filename}").status_code == 200
    assert client.get(f"/static/uploads/{filename}").status_code == 404

    token = csrf(client, "/")
    client.post("/logout", data={"_csrf_token": token})
    protected = client.get(f"/uploads/{filename}")
    assert protected.status_code == 302
    assert "/login" in protected.headers["Location"]


def test_gemini_uses_current_image_model_and_sends_key_in_header(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    client = app.test_client()
    create_admin(client)
    product_id = create_product(app, client)
    monkeypatch.setenv("GEMINI_API_KEY", "test-gemini-key")

    generated = base64.b64encode(png_bytes()).decode("ascii")
    response_payload = {
        "candidates": [{
            "content": {
                "parts": [
                    {"text": "Legenda de teste para a publicação."},
                    {"inlineData": {"mimeType": "image/png", "data": generated}},
                ]
            }
        }]
    }

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, size=-1):
            data = __import__("json").dumps(response_payload).encode("utf-8")
            return data[:size] if size >= 0 else data

    seen = {}

    def fake_urlopen(request, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(app_module.urllib.request, "urlopen", fake_urlopen)

    token = csrf(client, "/conteudo/criar-com-ia")
    response = client.post("/conteudo/criar-com-ia", data={
        "_csrf_token": token,
        "content_type": "story",
        "product_id": str(product_id),
        "revision": "Fundo mais limpo",
    }, follow_redirects=True)

    assert response.status_code == 200
    request = seen["request"]
    assert "models/gemini-3.1-flash-image:generateContent" in request.full_url
    assert "test-gemini-key" not in request.full_url
    assert request.get_header("X-goog-api-key") == "test-gemini-key"
    assert seen["timeout"] == 120

    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        row = conn.execute(
            "SELECT caption, image_filename FROM posts WHERE product_id=?",
            (product_id,),
        ).fetchone()
        assert row[0] == "Legenda de teste para a publicação."
        assert row[1].endswith(".png")
        assert (Path(app.config["UPLOAD_FOLDER"]) / row[1]).is_file()
    finally:
        conn.close()


def test_security_headers_are_present_on_public_health_endpoint(tmp_path):
    app = make_app(tmp_path)
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
