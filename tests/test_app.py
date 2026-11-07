import re

from app import create_app


def make_app(tmp_path):
    return create_app({
        "TESTING": True,
        "SECRET_KEY": "test-only-secret",
        "DATABASE": str(tmp_path / "test.sqlite3"),
        "UPLOAD_FOLDER": str(tmp_path / "uploads"),
    })


def csrf(client, path):
    response = client.get(path)
    assert response.status_code == 200
    match = re.search(
        r'name="_csrf_token" value="([^"]+)"',
        response.get_data(as_text=True),
    )
    assert match, "form must contain CSRF token"
    return match.group(1)


def test_health_endpoint(tmp_path):
    app = make_app(tmp_path)
    response = app.test_client().get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_setup_creates_first_user_and_protects_dashboard(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"] or "/configurar" in response.headers["Location"]

    token = csrf(client, "/configurar")
    response = client.post("/configurar", data={
        "_csrf_token": token,
        "username": "gabriel",
        "password": "senha-forte-de-teste-123",
        "confirmation": "senha-forte-de-teste-123",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert "Produtos cadastrados" in response.get_data(as_text=True)

    # First-run setup cannot be used to create another account.
    response = client.get("/configurar")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_rejects_wrong_password_and_accepts_correct_password(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    token = csrf(client, "/configurar")
    client.post("/configurar", data={
        "_csrf_token": token,
        "username": "gabriel",
        "password": "senha-forte-de-teste-123",
        "confirmation": "senha-forte-de-teste-123",
    })

    client.post("/logout", data={"_csrf_token": csrf(client, "/")})
    token = csrf(client, "/login")
    bad = client.post("/login", data={
        "_csrf_token": token, "username": "gabriel", "password": "errada"
    })
    assert "Usuário ou senha incorretos" in bad.get_data(as_text=True)

    token = csrf(client, "/login")
    good = client.post("/login", data={
        "_csrf_token": token,
        "username": "gabriel",
        "password": "senha-forte-de-teste-123",
    }, follow_redirects=True)
    assert good.status_code == 200
    assert "Produtos cadastrados" in good.get_data(as_text=True)


def test_post_without_csrf_is_rejected(tmp_path):
    app = make_app(tmp_path)
    response = app.test_client().post("/login", data={
        "username": "anyone", "password": "anything"
    })
    assert response.status_code == 400


def test_catalog_creates_product_with_separate_affiliate_link(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()

    token = csrf(client, "/configurar")
    client.post("/configurar", data={
        "_csrf_token": token,
        "username": "gabriel",
        "password": "senha-forte-de-teste-123",
        "confirmation": "senha-forte-de-teste-123",
    })

    token = csrf(client, "/produtos/novo")
    response = client.post("/produtos/novo", data={
        "_csrf_token": token,
        "name": "Tênis de corrida",
        "category": "Corrida",
        "price": "119,80",
        "affiliate_link": "https://shopee.com.br/teste-afiliado",
        "commission": "8,50",
        "notes": "Produto de teste",
    }, follow_redirects=True)

    assert response.status_code == 200
    assert "Tênis de corrida" in response.get_data(as_text=True)

    db = app.config["DATABASE"]
    import sqlite3
    conn = sqlite3.connect(db)
    try:
        product = conn.execute(
            "SELECT name, price, affiliate_link, commission FROM products"
        ).fetchone()
        assert product == (
            "Tênis de corrida", 119.8,
            "https://shopee.com.br/teste-afiliado", 8.5
        )
    finally:
        conn.close()


def test_catalog_accepts_multiple_product_photos(tmp_path):
    from io import BytesIO
    import sqlite3
    from PIL import Image

    image_buffer = BytesIO()
    Image.new("RGB", (2, 2), "orange").save(image_buffer, format="PNG")
    valid_png = image_buffer.getvalue()

    app = make_app(tmp_path)
    client = app.test_client()
    token = csrf(client, "/configurar")
    client.post("/configurar", data={
        "_csrf_token": token,
        "username": "gabriel",
        "password": "senha-forte-de-teste-123",
        "confirmation": "senha-forte-de-teste-123",
    })

    token = csrf(client, "/produtos/novo")
    response = client.post("/produtos/novo", data={
        "_csrf_token": token,
        "name": "Produto com fotos",
        "category": "Teste",
        "price": "25,00",
        "affiliate_link": "https://shopee.com.br/produto-teste",
        "photos": [
            (BytesIO(valid_png), "foto1.jpg"),
            (BytesIO(valid_png), "foto2.png"),
            (BytesIO(valid_png), "foto3.webp"),
        ],
    }, content_type="multipart/form-data", follow_redirects=True)

    assert response.status_code == 200
    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        main_photo = conn.execute(
            "SELECT image_filename FROM products WHERE name=?",
            ("Produto com fotos",)
        ).fetchone()[0]
        extra_count = conn.execute(
            "SELECT COUNT(*) FROM product_images WHERE product_id=("
            "SELECT id FROM products WHERE name=?)",
            ("Produto com fotos",)
        ).fetchone()[0]
        assert main_photo
        assert extra_count == 2
    finally:
        conn.close()



def login_first_user(client):
    token = csrf(client, "/configurar")
    client.post("/configurar", data={
        "_csrf_token": token,
        "username": "gabriel",
        "password": "senha-forte-de-teste-123",
        "confirmation": "senha-forte-de-teste-123",
    })


def test_shopee_search_page_requires_login(tmp_path):
    app = make_app(tmp_path)
    response = app.test_client().get("/produtos/buscar-shopee")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_shopee_search_page_renders_without_credentials_and_does_not_save_products(tmp_path, monkeypatch):
    from shopee_affiliate import ShopeeAffiliateClient, ShopeeAPIError

    app = make_app(tmp_path)
    client = app.test_client()
    login_first_user(client)
    monkeypatch.setattr(
        ShopeeAffiliateClient,
        "request",
        lambda *args, **kwargs: (_ for _ in ()).throw(ShopeeAPIError("API não configurada para teste")),
    )
    token = csrf(client, "/produtos/buscar-shopee")
    response = client.post(
        "/produtos/buscar-shopee",
        data={"_csrf_token": token, "keyword": "tênis de corrida"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "tênis de corrida" in response.get_data(as_text=True)
    assert "API não configurada para teste" in response.get_data(as_text=True)
    import sqlite3
    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0
    finally:
        conn.close()


def test_shopee_search_page_renders_mocked_offers_without_saving(tmp_path, monkeypatch):
    from shopee_affiliate import ShopeeAffiliateClient

    app = make_app(tmp_path)
    client = app.test_client()
    login_first_user(client)
    monkeypatch.setattr(
        ShopeeAffiliateClient,
        "request",
        lambda *args, **kwargs: {
            "productOfferV2": {
                "nodes": [{
                    "itemId": "12345",
                    "productName": "Tênis de teste",
                    "shopName": "Loja teste",
                    "price": 119.8,
                    "imageUrl": "https://example.com/tenis.jpg",
                    "offerLink": "https://example.com/oferta",
                    "productLink": "https://example.com/produto",
                    "commissionRate": "8%",
                    "sales": 10,
                    "ratingStar": 4.8,
                    "priceDiscountRate": 15,
                }],
                "pageInfo": {"page": 1, "limit": 10, "hasNextPage": False},
            }
        },
    )
    token = csrf(client, "/produtos/buscar-shopee")
    response = client.post(
        "/produtos/buscar-shopee",
        data={"_csrf_token": token, "keyword": "tênis"},
        follow_redirects=True,
    )
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Tênis de teste" in html
    assert "119,80" in html
    assert "Conferir link de afiliado" in html
    import sqlite3
    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0
    finally:
        conn.close()



def test_shopee_offer_import_saves_verified_affiliate_link_and_product(tmp_path, monkeypatch):
    import sqlite3
    from shopee_affiliate import ShopeeAffiliateClient

    app = make_app(tmp_path)
    client = app.test_client()
    login_first_user(client)
    offer = {
        "itemId": "98765",
        "productName": "Garrafa térmica de teste",
        "shopName": "Loja oficial",
        "price": 59.9,
        "commission": 4.25,
        "commissionRate": "8%",
        "offerLink": "https://s.shopee.com.br/link-afiliado-teste",
    }
    monkeypatch.setattr(
        ShopeeAffiliateClient,
        "request",
        lambda *args, **kwargs: {"productOfferV2": {"nodes": [offer], "pageInfo": {}}},
    )
    token = csrf(client, "/produtos/buscar-shopee")
    response = client.post(
        "/produtos/importar-oferta-shopee",
        data={
            "_csrf_token": token,
            "keyword": "garrafa térmica",
            "page": "1",
            "item_id": "98765",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "Produto importado com o link de afiliado" in response.get_data(as_text=True)
    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        saved = conn.execute(
            "SELECT name, price, affiliate_link, commission FROM products"
        ).fetchone()
        assert saved == (
            "Garrafa térmica de teste",
            59.9,
            "https://s.shopee.com.br/link-afiliado-teste",
            4.25,
        )
    finally:
        conn.close()


def test_shopee_offer_import_rejects_untrusted_link_and_tampered_item_id(tmp_path, monkeypatch):
    import sqlite3
    from shopee_affiliate import ShopeeAffiliateClient

    app = make_app(tmp_path)
    client = app.test_client()
    login_first_user(client)
    offer = {
        "itemId": "98765",
        "productName": "Produto com link externo",
        "price": 20,
        "offerLink": "https://example.com/not-an-affiliate-link",
    }
    monkeypatch.setattr(
        ShopeeAffiliateClient,
        "request",
        lambda *args, **kwargs: {"productOfferV2": {"nodes": [offer], "pageInfo": {}}},
    )
    token = csrf(client, "/produtos/buscar-shopee")
    response = client.post(
        "/produtos/importar-oferta-shopee",
        data={
            "_csrf_token": token,
            "keyword": "produto",
            "page": "1",
            "item_id": "98765",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "link de afiliado válido" in response.get_data(as_text=True)
    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        assert conn.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0
    finally:
        conn.close()

    token = csrf(client, "/produtos/buscar-shopee")
    response = client.post(
        "/produtos/importar-oferta-shopee",
        data={
            "_csrf_token": token,
            "keyword": "produto",
            "page": "1",
            "item_id": "ID-QUE-NAO-VEIO-DA-BUSCA",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "não está mais nos resultados" in response.get_data(as_text=True)

def test_catalog_renders_categories_even_when_there_are_no_products(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    login_first_user(client)

    response = client.get("/produtos")

    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Catálogos por categoria" in html
    assert "Academia" in html
    assert "Corrida" in html
    assert "Cadastrar primeiro produto" in html


def test_calendar_uses_category_colors_and_displays_full_day(tmp_path):
    import sqlite3

    app = make_app(tmp_path)
    client = app.test_client()
    login_first_user(client)
    day = "2026-11-07"

    categories = [
        ("Marketing", "orange", "09:00"),
        ("Produto", "blue", "10:00"),
        ("Pesquisa e oportunidades", "green", "11:00"),
        ("Urgente", "red", "12:00"),
        ("Organização", "pink", "13:00"),
        ("Outro compromisso", "gray", "14:00"),
    ]
    for category, color, time in categories:
        token = csrf(client, "/calendario")
        response = client.post("/calendario", data={
            "_csrf_token": token,
            "title": f"Tarefa {category}",
            "task_type": category,
            "due_at": f"{day}T{time}",
            "description": "Detalhes do compromisso",
        })
        assert response.status_code == 302

    response = client.get(f"/calendario?dia={day}")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    for category, color, time in categories:
        assert f"agenda-event-{color}" in html
        assert category in html
        assert time in html
    assert 'id="hora-00"' in html
    assert 'id="hora-23"' in html
    assert "Cor do compromisso" not in html

    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        saved = conn.execute(
            "SELECT task_type, color FROM calendar_tasks ORDER BY id"
        ).fetchall()
        assert saved == [(category, color) for category, color, _ in categories]
    finally:
        conn.close()


def test_calendar_rejects_invalid_category_and_uses_safe_default(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()
    login_first_user(client)
    token = csrf(client, "/calendario")

    response = client.post("/calendario", data={
        "_csrf_token": token,
        "title": "Compromisso sem categoria válida",
        "task_type": "cor-injetada",
        "due_at": "2026-11-07T15:00",
        "description": "Teste",
    })
    assert response.status_code == 302

    import sqlite3
    conn = sqlite3.connect(app.config["DATABASE"])
    try:
        saved = conn.execute(
            "SELECT task_type, color FROM calendar_tasks"
        ).fetchone()
        assert saved == ("Outro compromisso", "gray")
    finally:
        conn.close()
