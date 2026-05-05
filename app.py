from __future__ import annotations

import html
import os
import random
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from flask import Flask, redirect, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "site.db"
UPLOAD_DIR = BASE_DIR / "static" / "uploads"
ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

PUBLIC_PAGES = {
    "index.html",
    "about.html",
    "services.html",
    "catalog.html",
    "portfolio.html",
    "prices.html",
    "materials.html",
    "warranty.html",
    "care.html",
    "faq.html",
    "contacts.html",
    "request.html",
}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "practice-admin-session-key")

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")

REQUEST_STATUSES = {
    "new": "Новая",
    "in_work": "В работе",
    "done": "Завершена",
}

SERVICE_TYPES = [
    "Изготовление украшения",
    "Ремонт изделия",
    "Полировка и чистка",
    "Консультация",
]

CATALOG_SEED = [
    (
        "Кольцо «Лунная дорожка»",
        "Серебряное кольцо с мягкой фактурой и небольшим акцентным камнем. Подходит для повседневного образа.",
        "12 500 руб.",
        None,
    ),
    (
        "Подвеска «Капля света»",
        "Минималистичная подвеска с плавной формой, которую можно адаптировать под выбранный металл.",
        "8 900 руб.",
        None,
    ),
    (
        "Серьги «Тонкая линия»",
        "Лаконичные серьги ручной работы с полировкой и надежным креплением.",
        "10 400 руб.",
        None,
    ),
]

PORTFOLIO_SEED = [
    (
        "Обручальные кольца с матовой фактурой",
        "Парные кольца были изготовлены под индивидуальный размер клиента и дополнены внутренней гравировкой.",
        None,
    ),
    (
        "Восстановление семейной подвески",
        "Выполнены пайка крепления, чистка поверхности и бережная полировка после ремонта.",
        None,
    ),
    (
        "Серебряный браслет по эскизу",
        "Браслет изготовлен по эскизу клиента с корректировкой формы звеньев перед финальной сборкой.",
        None,
    ),
]

OLD_PLACEHOLDER_IMAGE_PATHS = {
    "static/uploads/catalog-ring.svg",
    "static/uploads/catalog-pendant.svg",
    "static/uploads/catalog-earrings.svg",
    "static/uploads/portfolio-rings.svg",
    "static/uploads/portfolio-pendant.svg",
    "static/uploads/portfolio-bracelet.svg",
}


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def escape(value: object) -> str:
    return html.escape(str(value or ""), quote=True)


def image_src(image_path: str | None) -> str:
    if not image_path:
        return ""
    if image_path.startswith("http://") or image_path.startswith("https://"):
        return image_path
    return "/" + image_path.lstrip("/").replace("\\", "/")


def render_image(image_path: str | None, alt: str, class_name: str) -> str:
    source = image_src(image_path)
    if not source:
        return ""
    return f'<img class="{class_name}" src="{source}" alt="{escape(alt)}">'


def render_admin_image(image_path: str | None, alt: str) -> str:
    source = image_src(image_path)
    if source:
        return f'<img class="admin-item-image" src="{source}" alt="{escape(alt)}">'
    return '<div class="admin-image-empty">Фото не загружено</div>'


def is_allowed_image(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_IMAGE_EXTENSIONS


def save_uploaded_image(file_storage) -> str | None:
    if not file_storage or not file_storage.filename:
        return None
    if not is_allowed_image(file_storage.filename):
        return None

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    extension = Path(file_storage.filename).suffix.lower()
    safe_name = secure_filename(Path(file_storage.filename).stem) or "image"
    filename = f"{datetime.now():%Y%m%d%H%M%S}_{uuid.uuid4().hex[:8]}_{safe_name}{extension}"
    destination = UPLOAD_DIR / filename
    file_storage.save(destination)
    return f"static/uploads/{filename}"


def delete_uploaded_image(image_path: str | None) -> None:
    if not image_path or image_path in OLD_PLACEHOLDER_IMAGE_PATHS:
        return

    relative_path = image_path.lstrip("/").replace("/", os.sep)
    target = (BASE_DIR / relative_path).resolve()
    upload_root = UPLOAD_DIR.resolve()
    if upload_root not in target.parents:
        return
    if target.exists():
        target.unlink()


def get_catalog_items(only_active: bool = True) -> list[sqlite3.Row]:
    query = "SELECT * FROM catalog_items"
    if only_active:
        query += " WHERE is_active = 1"
    query += " ORDER BY id DESC"
    with get_connection() as connection:
        return connection.execute(query).fetchall()


def get_portfolio_items(only_active: bool = True) -> list[sqlite3.Row]:
    query = "SELECT * FROM portfolio_items"
    if only_active:
        query += " WHERE is_active = 1"
    query += " ORDER BY id DESC"
    with get_connection() as connection:
        return connection.execute(query).fetchall()


def get_home_gallery_items(limit: int = 6) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    with get_connection() as connection:
        catalog_rows = connection.execute(
            """
            SELECT id, title, description, price, image_path
            FROM catalog_items
            WHERE is_active = 1
              AND image_path IS NOT NULL
              AND TRIM(image_path) != ''
            ORDER BY id DESC
            """
        ).fetchall()
        portfolio_rows = connection.execute(
            """
            SELECT id, title, description, image_path
            FROM portfolio_items
            WHERE is_active = 1
              AND image_path IS NOT NULL
              AND TRIM(image_path) != ''
            ORDER BY id DESC
            """
        ).fetchall()

    for item in catalog_rows:
        if item["image_path"] in OLD_PLACEHOLDER_IMAGE_PATHS:
            continue
        items.append(
            {
                "title": item["title"],
                "description": item["description"],
                "image_path": item["image_path"],
                "href": f"/catalog.html#catalog-item-{item['id']}",
                "label": "Каталог",
                "meta": item["price"],
            }
        )

    for item in portfolio_rows:
        if item["image_path"] in OLD_PLACEHOLDER_IMAGE_PATHS:
            continue
        items.append(
            {
                "title": item["title"],
                "description": item["description"],
                "image_path": item["image_path"],
                "href": f"/portfolio.html#portfolio-item-{item['id']}",
                "label": "Портфолио",
                "meta": "Выполненная работа",
            }
        )

    random.shuffle(items)
    return items[:limit]


def render_home_gallery_cards(items: list[dict[str, str]]) -> str:
    if not items:
        return """
          <div class="empty-state">
            <p>Фотографии появятся здесь после загрузки изображений в каталог или портфолио через административную часть сайта.</p>
          </div>
"""

    cards = []
    for item in items:
        cards.append(
            f"""
          <a class="featured-photo-card" href="{escape(item['href'])}">
            {render_image(item['image_path'], item['title'], "featured-photo")}
            <span class="featured-photo-label">{escape(item['label'])}</span>
            <span class="featured-photo-body">
              <strong>{escape(item['title'])}</strong>
              <small>{escape(item['meta'])}</small>
            </span>
          </a>
"""
        )
    return "".join(cards)


def render_public_header(active_page: str) -> str:
    links = [
        ("about.html", "О мастерской", "about"),
        ("index.html", "Главная", "index"),
        ("services.html", "Услуги", "services"),
        ("catalog.html", "Каталог", "catalog"),
        ("portfolio.html", "Портфолио", "portfolio"),
        ("request.html", "Заявка", "request"),
        ("contacts.html", "Контакты", "contacts"),
    ]
    nav_links = []
    for href, label, key in links:
        active_class = ' class="active"' if key == active_page else ""
        nav_links.append(f'<a{active_class} href="/{href}">{label}</a>')

    return f"""
    <header class="site-header">
      <a class="brand" href="/index.html" aria-label="Главная страница">
        <span class="brand-mark">ЮМ</span>
        <span>
          <strong>Ювелирная мастерская</strong>
          <small>изготовление и ремонт ювелирных украшений</small>
        </span>
      </a>

      <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="main-nav">
        Меню
      </button>

      <nav id="main-nav" class="main-nav" aria-label="Основное меню">
        {''.join(nav_links)}
      </nav>
    </header>
"""


def render_footer() -> str:
    return """
    <footer class="site-footer">
      <div class="footer-inner">
        <span>Калинин Александр Сергеевич</span>
        <div class="footer-links" aria-label="Дополнительная навигация">
          <a href="/prices.html">Цены</a>
          <a href="/materials.html">Материалы</a>
          <a href="/warranty.html">Гарантия</a>
          <a href="/care.html">Уход</a>
          <a href="/faq.html">FAQ</a>
        </div>
      </div>
    </footer>
"""


def render_page(title: str, active_page: str, breadcrumb: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)} | Ювелирная мастерская</title>
    <link rel="stylesheet" href="/static/css/styles.css">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  </head>
  <body>
    {render_public_header(active_page)}
    <main>
      <nav class="breadcrumbs" aria-label="Хлебные крошки">
        <span>{escape(breadcrumb)}</span>
      </nav>
      {content}
    </main>
    {render_footer()}
    <script src="/static/js/main.js"></script>
  </body>
</html>"""


def render_admin_nav(active_page: str) -> str:
    links = [
        ("/admin/requests", "Заявки", "requests"),
        ("/admin/catalog", "Каталог", "catalog"),
        ("/admin/portfolio", "Портфолио", "portfolio"),
    ]
    nav_links = []
    for href, label, key in links:
        active_class = ' class="active"' if key == active_page else ""
        nav_links.append(f'<a{active_class} href="{href}">{label}</a>')

    return f"""
      <nav id="main-nav" class="main-nav" aria-label="Основное меню">
        {''.join(nav_links)}
        <form class="nav-logout" action="/admin/logout" method="post">
          <button type="submit">Выйти</button>
        </form>
      </nav>
"""


def render_admin_header(active_page: str) -> str:
    return f"""
    <header class="site-header">
      <a class="brand" href="/index.html" aria-label="Главная страница">
        <span class="brand-mark">ЮМ</span>
        <span>
          <strong>Ювелирная мастерская</strong>
          <small>изготовление и ремонт ювелирных украшений</small>
        </span>
      </a>

      <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="main-nav">
        Меню
      </button>

      {render_admin_nav(active_page)}
    </header>
"""


def render_admin_page(title: str, active_page: str, breadcrumb: str, content: str) -> str:
    return f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{escape(title)} | Ювелирная мастерская</title>
    <link rel="stylesheet" href="/static/css/styles.css">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  </head>
  <body>
    {render_admin_header(active_page)}
    <main>
      <nav class="breadcrumbs" aria-label="Хлебные крошки">
        <span>Администрирование / {escape(breadcrumb)}</span>
      </nav>
      {content}
    </main>
    {render_footer()}
    <script src="/static/js/main.js"></script>
  </body>
</html>"""


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS request_statuses (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO request_statuses (code, name, sort_order)
            VALUES (?, ?, ?)
            """,
            [
                (code, name, index)
                for index, (code, name) in enumerate(REQUEST_STATUSES.items(), start=1)
            ],
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS service_types (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                is_active INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        connection.executemany(
            """
            INSERT OR IGNORE INTO service_types (name)
            VALUES (?)
            """,
            [(name,) for name in SERVICE_TYPES],
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS catalog_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                price TEXT NOT NULL,
                image_path TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        if connection.execute("SELECT COUNT(*) FROM catalog_items").fetchone()[0] == 0:
            connection.executemany(
                """
                INSERT INTO catalog_items (
                    title,
                    description,
                    price,
                    image_path,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (*item, datetime.now().strftime("%d.%m.%Y %H:%M"))
                    for item in CATALOG_SEED
                ],
            )
        connection.execute(
            f"""
            UPDATE catalog_items
            SET image_path = NULL
            WHERE image_path IN ({",".join("?" for _ in OLD_PLACEHOLDER_IMAGE_PATHS)})
            """,
            tuple(OLD_PLACEHOLDER_IMAGE_PATHS),
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS portfolio_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                image_path TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
            """
        )
        if connection.execute("SELECT COUNT(*) FROM portfolio_items").fetchone()[0] == 0:
            connection.executemany(
                """
                INSERT INTO portfolio_items (
                    title,
                    description,
                    image_path,
                    created_at
                )
                VALUES (?, ?, ?, ?)
                """,
                [
                    (*item, datetime.now().strftime("%d.%m.%Y %H:%M"))
                    for item in PORTFOLIO_SEED
                ],
            )
        connection.execute(
            f"""
            UPDATE portfolio_items
            SET image_path = NULL
            WHERE image_path IN ({",".join("?" for _ in OLD_PLACEHOLDER_IMAGE_PATHS)})
            """,
            tuple(OLD_PLACEHOLDER_IMAGE_PATHS),
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                client_contact TEXT NOT NULL,
                service_type TEXT NOT NULL,
                budget TEXT,
                comment TEXT,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL
            )
            """
        )
        columns = connection.execute("PRAGMA table_info(requests)").fetchall()
        column_names = {column["name"] for column in columns}
        if "status" not in column_names:
            connection.execute(
                "ALTER TABLE requests ADD COLUMN status TEXT NOT NULL DEFAULT 'new'"
            )


def is_admin_logged_in() -> bool:
    return session.get("admin_logged_in") is True


def admin_redirect():
    return redirect(url_for("admin_login", next=request.full_path.rstrip("?")))


@app.route("/")
@app.route("/index.html")
def index():
    featured_gallery = render_home_gallery_cards(get_home_gallery_items())
    content = f"""
      <section class="hero">
        <div class="hero-text">
          <p class="eyebrow">Ювелирная мастерская</p>
          <h1>Изготовление, ремонт и подбор ювелирных украшений</h1>
          <p>
            Сайт помогает показать работы мастерской, принять заявку клиента
            и передать обращение в административную часть для дальнейшей обработки.
          </p>
          <a class="primary-button" href="/catalog.html">Смотреть каталог</a>
          <a class="text-link" href="/request.html">Оставить заявку</a>
        </div>
      </section>

      <section class="section">
        <div class="section-heading">
          <p class="eyebrow">Витрина</p>
          <h2>Случайные фото изделий</h2>
          <p>Фотографии автоматически берутся из активных карточек каталога и портфолио.</p>
        </div>
        <div class="featured-photo-grid">
          {featured_gallery}
        </div>
      </section>

      <section class="section">
        <div class="section-heading">
          <p class="eyebrow">Что можно сделать</p>
          <h2>Основные направления мастерской</h2>
        </div>
        <div class="cards">
          <article class="card">
            <h3>Индивидуальный заказ</h3>
            <p>Создание украшений по описанию, эскизу или примеру клиента.</p>
          </article>
          <article class="card">
            <h3>Ремонт украшений</h3>
            <p>Восстановление креплений, пайка, чистка, полировка и подгонка размера.</p>
          </article>
          <article class="card">
            <h3>Готовые изделия</h3>
            <p>Каталог с изделиями, которые можно купить или адаптировать под заказ.</p>
          </article>
        </div>
      </section>

      <section class="section process-section">
        <div class="section-heading">
          <p class="eyebrow">Процесс</p>
          <h2>Как проходит работа</h2>
        </div>
        <ol class="steps">
          <li>Клиент выбирает изделие в каталоге или описывает задачу в форме.</li>
          <li>Заявка сохраняется в базе данных и попадает в административную часть.</li>
          <li>Администратор уточняет детали, меняет статус и передает заказ в работу.</li>
          <li>После согласования мастер выполняет изделие или ремонт.</li>
        </ol>
      </section>

      <section class="section contact-section">
        <div class="section-heading">
          <p class="eyebrow">Заявка</p>
          <h2>Оставьте обращение для мастерской</h2>
          <p>Опишите изделие, ремонт или пожелания к материалу. После отправки заявка появится у администратора сайта.</p>
          <a class="primary-button" href="/request.html">Оставить заявку</a>
        </div>
      </section>
"""
    return render_page("Главная", "index", "Главная", content)


@app.route("/favicon.svg")
def favicon_svg():
    return send_from_directory(BASE_DIR, "favicon.svg", mimetype="image/svg+xml")


@app.route("/favicon.ico")
def favicon_ico():
    return send_from_directory(BASE_DIR, "favicon.svg", mimetype="image/svg+xml")


@app.route("/catalog.html")
def catalog_page():
    items = get_catalog_items()
    cards = []
    for item in items:
        title = escape(item["title"])
        description = escape(item["description"])
        price = escape(item["price"])
        image_html = render_image(item["image_path"], item["title"], "item-image")
        request_href = (
            "/request.html?"
            f"item={quote(item['title'])}&"
            f"price={quote(item['price'])}"
        )
        cards.append(
            f"""
          <article id="catalog-item-{item['id']}" class="item-card">
            {image_html}
            <div class="item-body">
              <h3>{title}</h3>
              <p>{description}</p>
              <p class="item-price">{price}</p>
              <a class="primary-button" href="{request_href}">Оставить заявку</a>
            </div>
          </article>
"""
        )

    content = f"""
      <section class="hero">
        <div class="hero-text">
          <p class="eyebrow">Каталог</p>
          <h1>Изделия для заказа и покупки</h1>
          <p>
            В каталоге представлены готовые позиции и изделия, которые можно
            адаптировать под размер, материал и пожелания клиента.
          </p>
          <a class="primary-button" href="/request.html">Уточнить стоимость</a>
        </div>
      </section>

      <section class="section">
        <div class="section-heading">
          <p class="eyebrow">В наличии и под заказ</p>
          <h2>Каталог изделий</h2>
          <p>Нажмите «Оставить заявку», чтобы обсудить конкретное изделие с мастером.</p>
        </div>
        <div class="item-grid">
          {''.join(cards)}
        </div>
      </section>
"""
    return render_page("Каталог", "catalog", "Каталог", content)


@app.route("/portfolio.html")
def portfolio_page():
    items = get_portfolio_items()
    cards = []
    for item in items:
        title = escape(item["title"])
        description = escape(item["description"])
        image_html = render_image(item["image_path"], item["title"], "item-image")
        cards.append(
            f"""
          <article id="portfolio-item-{item['id']}" class="item-card">
            {image_html}
            <div class="item-body">
              <h3>{title}</h3>
              <p>{description}</p>
              <a class="text-link" href="/request.html?item={quote(item['title'])}">Обсудить похожий заказ</a>
            </div>
          </article>
"""
        )

    content = f"""
      <section class="hero">
        <div class="hero-text">
          <p class="eyebrow">Портфолио</p>
          <h1>Проданные изделия и выполненные работы</h1>
          <p>
            Здесь собраны примеры уже выполненных заказов: изготовление,
            восстановление и оформление украшений для клиентов мастерской.
          </p>
          <a class="primary-button" href="/request.html">Обсудить похожий заказ</a>
        </div>
      </section>

      <section class="section">
        <div class="section-heading">
          <p class="eyebrow">Готовые работы</p>
          <h2>Портфолио мастерской</h2>
          <p>Фотографии можно обновлять через административную часть сайта.</p>
        </div>
        <div class="item-grid">
          {''.join(cards)}
        </div>
      </section>
"""
    return render_page("Портфолио", "portfolio", "Портфолио", content)


@app.route("/request", methods=["POST"])
def create_request():
    client_name = request.form.get("client-name", "").strip()
    client_contact = request.form.get("client-contact", "").strip()
    service_type = request.form.get("service-type", "").strip()
    budget = request.form.get("budget", "").strip()
    comment = request.form.get("comment", "").strip()

    if not client_name or not client_contact:
        return redirect(url_for("serve_page", page_name="request.html", status="error"))

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO requests (
                client_name,
                client_contact,
                service_type,
                budget,
                comment,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                client_name,
                client_contact,
                service_type,
                budget,
                comment,
                datetime.now().strftime("%d.%m.%Y %H:%M"),
            ),
        )

    return redirect(url_for("serve_page", page_name="request.html", status="sent"))


@app.route("/admin")
def admin_index():
    return redirect(url_for("admin_requests"))


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    next_page = request.args.get("next") or request.form.get("next") or url_for("admin_requests")
    if not next_page.startswith("/admin"):
        next_page = url_for("admin_requests")

    error_message = ""
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(next_page)

        error_message = (
            '<p class="form-note form-alert form-alert-error">'
            "Неверный пароль администратора."
            "</p>"
        )

    return f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Вход администратора | Ювелирная мастерская</title>
    <link rel="stylesheet" href="/static/css/styles.css">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  </head>
  <body>
    <header class="site-header">
      <a class="brand" href="/index.html" aria-label="Главная страница">
        <span class="brand-mark">ЮМ</span>
        <span>
          <strong>Ювелирная мастерская</strong>
          <small>изготовление и ремонт ювелирных украшений</small>
        </span>
      </a>

      <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="main-nav">
        Меню
      </button>

      <nav id="main-nav" class="main-nav" aria-label="Основное меню">
        <a href="/index.html">Главная</a>
      </nav>
    </header>

    <main>
      <nav class="breadcrumbs" aria-label="Хлебные крошки">
        <span>Администрирование / Вход</span>
      </nav>

      <section class="section contact-section login-section">
        <div class="section-heading">
          <p class="eyebrow">Админка</p>
          <h1>Вход администратора</h1>
          <p>Введите пароль, чтобы открыть список клиентских заявок.</p>
        </div>

        <form class="login-form" action="/admin/login" method="post">
          <input type="hidden" name="next" value="{html.escape(next_page)}">
          <div class="form-field">
            <label for="admin-password">Пароль</label>
            <input id="admin-password" name="password" type="password" required>
          </div>
          <button class="primary-button" type="submit">Войти</button>
          {error_message}
        </form>
      </section>
    </main>

    <script src="/static/js/main.js"></script>
  </body>
</html>"""


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))


@app.route("/admin/catalog", methods=["GET", "POST"])
def admin_catalog():
    if not is_admin_logged_in():
        return admin_redirect()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "").strip()
        image_path = save_uploaded_image(request.files.get("image"))

        if title and description and price:
            with get_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO catalog_items (
                        title,
                        description,
                        price,
                        image_path,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        title,
                        description,
                        price,
                        image_path,
                        datetime.now().strftime("%d.%m.%Y %H:%M"),
                    ),
                )

        return redirect(url_for("admin_catalog"))

    items = get_catalog_items(only_active=False)
    item_cards = []
    for item in items:
        item_cards.append(
            f"""
          <article class="admin-item-card">
            {render_admin_image(item['image_path'], item['title'])}
            <form class="admin-item-form" action="/admin/catalog/{item['id']}" method="post" enctype="multipart/form-data">
              <div class="form-field">
                <label for="catalog-title-{item['id']}">Название</label>
                <input id="catalog-title-{item['id']}" name="title" type="text" value="{escape(item['title'])}" required>
              </div>
              <div class="form-field">
                <label for="catalog-price-{item['id']}">Цена</label>
                <input id="catalog-price-{item['id']}" name="price" type="text" value="{escape(item['price'])}" required>
              </div>
              <div class="form-field">
                <label for="catalog-description-{item['id']}">Описание</label>
                <textarea id="catalog-description-{item['id']}" name="description" required>{escape(item['description'])}</textarea>
              </div>
              <div class="form-field">
                <label for="catalog-image-{item['id']}">Новое фото</label>
                <input id="catalog-image-{item['id']}" name="image" type="file" accept="image/png,image/jpeg,image/webp">
              </div>
              <button class="primary-button" type="submit">Сохранить</button>
            </form>
            <div class="admin-actions">
              <form action="/admin/catalog/{item['id']}/image/delete" method="post">
                <button class="secondary-button" type="submit">Удалить фото</button>
              </form>
              <form action="/admin/catalog/{item['id']}/delete" method="post">
                <button class="danger-button" type="submit">Удалить изделие</button>
              </form>
            </div>
          </article>
"""
        )

    content = f"""
      <section class="section contact-section">
        <div class="section-heading">
          <p class="eyebrow">Админка</p>
          <h1>Управление каталогом</h1>
          <p>Добавляйте изделия для продажи, редактируйте описания, цены и фотографии.</p>
        </div>

        <form class="admin-create-form" action="/admin/catalog" method="post" enctype="multipart/form-data">
          <div class="form-grid">
            <div class="form-field">
              <label for="catalog-title">Название</label>
              <input id="catalog-title" name="title" type="text" required>
            </div>
            <div class="form-field">
              <label for="catalog-price">Цена</label>
              <input id="catalog-price" name="price" type="text" placeholder="например, 12 500 руб." required>
            </div>
            <div class="form-field form-field-wide">
              <label for="catalog-description">Описание</label>
              <textarea id="catalog-description" name="description" required></textarea>
            </div>
            <div class="form-field form-field-wide">
              <label for="catalog-image">Фото</label>
              <input id="catalog-image" name="image" type="file" accept="image/png,image/jpeg,image/webp">
            </div>
          </div>
          <button class="primary-button" type="submit">Добавить изделие</button>
        </form>
      </section>

      <section class="section">
        <div class="section-heading">
          <p class="eyebrow">Список</p>
          <h2>Изделия каталога</h2>
        </div>
        <div class="admin-item-grid">
          {''.join(item_cards)}
        </div>
      </section>
"""
    return render_admin_page("Каталог", "catalog", "Каталог", content)


@app.route("/admin/catalog/<int:item_id>", methods=["POST"])
def update_catalog_item(item_id: int):
    if not is_admin_logged_in():
        return admin_redirect()

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    price = request.form.get("price", "").strip()
    new_image_path = save_uploaded_image(request.files.get("image"))

    with get_connection() as connection:
        current = connection.execute(
            "SELECT image_path FROM catalog_items WHERE id = ?",
            (item_id,),
        ).fetchone()
        if title and description and price:
            if new_image_path:
                if current:
                    delete_uploaded_image(current["image_path"])
                connection.execute(
                    """
                    UPDATE catalog_items
                    SET title = ?, description = ?, price = ?, image_path = ?
                    WHERE id = ?
                    """,
                    (title, description, price, new_image_path, item_id),
                )
            else:
                connection.execute(
                    """
                    UPDATE catalog_items
                    SET title = ?, description = ?, price = ?
                    WHERE id = ?
                    """,
                    (title, description, price, item_id),
                )

    return redirect(url_for("admin_catalog"))


@app.route("/admin/catalog/<int:item_id>/image/delete", methods=["POST"])
def delete_catalog_image(item_id: int):
    if not is_admin_logged_in():
        return admin_redirect()

    with get_connection() as connection:
        current = connection.execute(
            "SELECT image_path FROM catalog_items WHERE id = ?",
            (item_id,),
        ).fetchone()
        if current:
            delete_uploaded_image(current["image_path"])
            connection.execute(
                "UPDATE catalog_items SET image_path = ? WHERE id = ?",
                (None, item_id),
            )

    return redirect(url_for("admin_catalog"))


@app.route("/admin/catalog/<int:item_id>/delete", methods=["POST"])
def delete_catalog_item(item_id: int):
    if not is_admin_logged_in():
        return admin_redirect()

    with get_connection() as connection:
        current = connection.execute(
            "SELECT image_path FROM catalog_items WHERE id = ?",
            (item_id,),
        ).fetchone()
        if current:
            delete_uploaded_image(current["image_path"])
            connection.execute("DELETE FROM catalog_items WHERE id = ?", (item_id,))

    return redirect(url_for("admin_catalog"))


@app.route("/admin/portfolio", methods=["GET", "POST"])
def admin_portfolio():
    if not is_admin_logged_in():
        return admin_redirect()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        image_path = save_uploaded_image(request.files.get("image"))

        if title and description:
            with get_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO portfolio_items (
                        title,
                        description,
                        image_path,
                        created_at
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        title,
                        description,
                        image_path,
                        datetime.now().strftime("%d.%m.%Y %H:%M"),
                    ),
                )

        return redirect(url_for("admin_portfolio"))

    items = get_portfolio_items(only_active=False)
    item_cards = []
    for item in items:
        item_cards.append(
            f"""
          <article class="admin-item-card">
            {render_admin_image(item['image_path'], item['title'])}
            <form class="admin-item-form" action="/admin/portfolio/{item['id']}" method="post" enctype="multipart/form-data">
              <div class="form-field">
                <label for="portfolio-title-{item['id']}">Название</label>
                <input id="portfolio-title-{item['id']}" name="title" type="text" value="{escape(item['title'])}" required>
              </div>
              <div class="form-field">
                <label for="portfolio-description-{item['id']}">Описание</label>
                <textarea id="portfolio-description-{item['id']}" name="description" required>{escape(item['description'])}</textarea>
              </div>
              <div class="form-field">
                <label for="portfolio-image-{item['id']}">Новое фото</label>
                <input id="portfolio-image-{item['id']}" name="image" type="file" accept="image/png,image/jpeg,image/webp">
              </div>
              <button class="primary-button" type="submit">Сохранить</button>
            </form>
            <div class="admin-actions">
              <form action="/admin/portfolio/{item['id']}/image/delete" method="post">
                <button class="secondary-button" type="submit">Удалить фото</button>
              </form>
              <form action="/admin/portfolio/{item['id']}/delete" method="post">
                <button class="danger-button" type="submit">Удалить работу</button>
              </form>
            </div>
          </article>
"""
        )

    content = f"""
      <section class="section contact-section">
        <div class="section-heading">
          <p class="eyebrow">Админка</p>
          <h1>Управление портфолио</h1>
          <p>Добавляйте проданные изделия и выполненные работы, меняйте описание и фотографии.</p>
        </div>

        <form class="admin-create-form" action="/admin/portfolio" method="post" enctype="multipart/form-data">
          <div class="form-grid">
            <div class="form-field form-field-wide">
              <label for="portfolio-title">Название</label>
              <input id="portfolio-title" name="title" type="text" required>
            </div>
            <div class="form-field form-field-wide">
              <label for="portfolio-description">Описание</label>
              <textarea id="portfolio-description" name="description" required></textarea>
            </div>
            <div class="form-field form-field-wide">
              <label for="portfolio-image">Фото</label>
              <input id="portfolio-image" name="image" type="file" accept="image/png,image/jpeg,image/webp">
            </div>
          </div>
          <button class="primary-button" type="submit">Добавить работу</button>
        </form>
      </section>

      <section class="section">
        <div class="section-heading">
          <p class="eyebrow">Список</p>
          <h2>Работы портфолио</h2>
        </div>
        <div class="admin-item-grid">
          {''.join(item_cards)}
        </div>
      </section>
"""
    return render_admin_page("Портфолио", "portfolio", "Портфолио", content)


@app.route("/admin/portfolio/<int:item_id>", methods=["POST"])
def update_portfolio_item(item_id: int):
    if not is_admin_logged_in():
        return admin_redirect()

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    new_image_path = save_uploaded_image(request.files.get("image"))

    with get_connection() as connection:
        current = connection.execute(
            "SELECT image_path FROM portfolio_items WHERE id = ?",
            (item_id,),
        ).fetchone()
        if title and description:
            if new_image_path:
                if current:
                    delete_uploaded_image(current["image_path"])
                connection.execute(
                    """
                    UPDATE portfolio_items
                    SET title = ?, description = ?, image_path = ?
                    WHERE id = ?
                    """,
                    (title, description, new_image_path, item_id),
                )
            else:
                connection.execute(
                    """
                    UPDATE portfolio_items
                    SET title = ?, description = ?
                    WHERE id = ?
                    """,
                    (title, description, item_id),
                )

    return redirect(url_for("admin_portfolio"))


@app.route("/admin/portfolio/<int:item_id>/image/delete", methods=["POST"])
def delete_portfolio_image(item_id: int):
    if not is_admin_logged_in():
        return admin_redirect()

    with get_connection() as connection:
        current = connection.execute(
            "SELECT image_path FROM portfolio_items WHERE id = ?",
            (item_id,),
        ).fetchone()
        if current:
            delete_uploaded_image(current["image_path"])
            connection.execute(
                "UPDATE portfolio_items SET image_path = ? WHERE id = ?",
                (None, item_id),
            )

    return redirect(url_for("admin_portfolio"))


@app.route("/admin/portfolio/<int:item_id>/delete", methods=["POST"])
def delete_portfolio_item(item_id: int):
    if not is_admin_logged_in():
        return admin_redirect()

    with get_connection() as connection:
        current = connection.execute(
            "SELECT image_path FROM portfolio_items WHERE id = ?",
            (item_id,),
        ).fetchone()
        if current:
            delete_uploaded_image(current["image_path"])
            connection.execute("DELETE FROM portfolio_items WHERE id = ?", (item_id,))

    return redirect(url_for("admin_portfolio"))


@app.route("/admin/requests/<int:request_id>/status", methods=["POST"])
def update_request_status(request_id: int):
    if not is_admin_logged_in():
        return admin_redirect()

    status = request.form.get("status", "new")
    current_filter = request.form.get("current-filter", "all")
    if status not in REQUEST_STATUSES:
        status = "new"
    if current_filter not in REQUEST_STATUSES:
        current_filter = "all"

    with get_connection() as connection:
        connection.execute(
            "UPDATE requests SET status = ? WHERE id = ?",
            (status, request_id),
        )

    return redirect(url_for("admin_requests", status=current_filter))


@app.route("/admin/requests")
def admin_requests():
    if not is_admin_logged_in():
        return admin_redirect()

    active_filter = request.args.get("status", "all")
    if active_filter not in REQUEST_STATUSES:
        active_filter = "all"

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                client_name,
                client_contact,
                service_type,
                budget,
                comment,
                status,
                created_at
            FROM requests
            ORDER BY id DESC
            """
        ).fetchall()

    status_counts = {status: 0 for status in REQUEST_STATUSES}
    for row in rows:
        row_status = row["status"] if row["status"] in REQUEST_STATUSES else "new"
        status_counts[row_status] += 1

    filtered_rows = [
        row
        for row in rows
        if active_filter == "all"
        or (row["status"] if row["status"] in REQUEST_STATUSES else "new") == active_filter
    ]

    status_cards = []
    for status, label in REQUEST_STATUSES.items():
        status_cards.append(
            '<div class="admin-stat">'
            f'<span class="status-badge status-{status}">{label}</span>'
            f'<strong>{status_counts[status]}</strong>'
            "</div>"
        )

    filter_options = [("all", "Все заявки"), *REQUEST_STATUSES.items()]
    filter_links = []
    for value, label in filter_options:
        href = "/admin/requests" if value == "all" else f"/admin/requests?status={value}"
        active_class = " active" if value == active_filter else ""
        filter_links.append(
            f'<a class="filter-link{active_class}" href="{href}">{label}</a>'
        )

    def render_status_form(row: sqlite3.Row) -> str:
        options = []
        current_status = row["status"] if row["status"] in REQUEST_STATUSES else "new"
        for value, label in REQUEST_STATUSES.items():
            selected = " selected" if value == current_status else ""
            options.append(f'<option value="{value}"{selected}>{label}</option>')

        return (
            f'<form class="status-form" action="/admin/requests/{row["id"]}/status" method="post">'
            f'<span class="status-badge status-{current_status}">'
            f"{REQUEST_STATUSES[current_status]}"
            "</span>"
            f'<select name="status" aria-label="Статус заявки {row["id"]}">'
            f"{''.join(options)}"
            "</select>"
            f'<input type="hidden" name="current-filter" value="{active_filter}">'
            '<button type="submit">Сохранить</button>'
            "</form>"
        )

    table_rows = []
    for row in filtered_rows:
        table_rows.append(
            "<tr>"
            f"<td class=\"request-id\">#{row['id']}</td>"
            f"<td class=\"request-date\">{html.escape(row['created_at'])}</td>"
            f"<td>{render_status_form(row)}</td>"
            f"<td><strong>{html.escape(row['client_name'])}</strong></td>"
            f"<td class=\"request-contact\">{html.escape(row['client_contact'])}</td>"
            f"<td>{html.escape(row['service_type'])}</td>"
            f"<td>{html.escape(row['budget'] or '-')}</td>"
            f"<td class=\"request-comment\">{html.escape(row['comment'] or '-')}</td>"
            "</tr>"
        )

    if not table_rows:
        table_rows.append(
            '<tr><td colspan="8">Нет заявок для выбранного фильтра.</td></tr>'
        )

    return f"""<!doctype html>
<html lang="ru">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Заявки | Ювелирная мастерская</title>
    <link rel="stylesheet" href="/static/css/styles.css">
    <link rel="icon" href="/favicon.svg" type="image/svg+xml">
  </head>
  <body>
    {render_admin_header("requests")}

    <main>
      <nav class="breadcrumbs" aria-label="Хлебные крошки">
        <span>Администрирование / Заявки</span>
      </nav>

      <section class="section contact-section">
        <div class="section-heading">
          <p class="eyebrow">Админка</p>
          <h1>Заявки клиентов</h1>
          <p>На этой странице отображаются обращения, сохраненные через форму заявки.</p>
        </div>

        <div class="admin-stats" aria-label="Статистика заявок">
          {''.join(status_cards)}
        </div>

        <div class="admin-filters" aria-label="Фильтр заявок">
          {''.join(filter_links)}
        </div>

        <div class="table-wrap">
          <table class="requests-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Дата</th>
                <th>Статус</th>
                <th>Имя</th>
                <th>Контакт</th>
                <th>Услуга</th>
                <th>Бюджет</th>
                <th>Комментарий</th>
              </tr>
            </thead>
            <tbody>
              {''.join(table_rows)}
            </tbody>
          </table>
        </div>
      </section>
    </main>

    <footer class="site-footer">
      <div class="footer-inner">
        <span>Калинин Александр Сергеевич</span>
        <div class="footer-links">
          <a href="/index.html">Сайт</a>
          <a href="/request.html">Форма заявки</a>
        </div>
      </div>
    </footer>

    <script src="/static/js/main.js"></script>
  </body>
</html>"""


@app.route("/<path:page_name>")
def serve_page(page_name: str):
    if page_name in PUBLIC_PAGES:
        return send_from_directory(BASE_DIR, page_name)
    return "Страница не найдена", 404

init_db()


if __name__ == "__main__":
    app.run(debug=True)
