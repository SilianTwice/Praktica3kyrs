from __future__ import annotations

import html
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, redirect, request, send_from_directory, session, url_for


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "site.db"

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


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
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
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/favicon.svg")
def favicon_svg():
    return send_from_directory(BASE_DIR, "favicon.svg", mimetype="image/svg+xml")


@app.route("/favicon.ico")
def favicon_ico():
    return send_from_directory(BASE_DIR, "favicon.svg", mimetype="image/svg+xml")


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
        <a class="active" href="/admin/requests">Заявки</a>
        <form class="nav-logout" action="/admin/logout" method="post">
          <button type="submit">Выйти</button>
        </form>
      </nav>
    </header>

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
