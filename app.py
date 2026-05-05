from __future__ import annotations

import html
import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, redirect, request, send_from_directory, url_for


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


@app.route("/admin/requests/<int:request_id>/status", methods=["POST"])
def update_request_status(request_id: int):
    status = request.form.get("status", "new")
    if status not in REQUEST_STATUSES:
        status = "new"

    with get_connection() as connection:
        connection.execute(
            "UPDATE requests SET status = ? WHERE id = ?",
            (status, request_id),
        )

    return redirect(url_for("admin_requests"))


@app.route("/admin/requests")
def admin_requests():
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

    status_cards = []
    for status, label in REQUEST_STATUSES.items():
        status_cards.append(
            '<div class="admin-stat">'
            f'<span class="status-badge status-{status}">{label}</span>'
            f'<strong>{status_counts[status]}</strong>'
            "</div>"
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
            '<button type="submit">Сохранить</button>'
            "</form>"
        )

    table_rows = []
    for row in rows:
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
            '<tr><td colspan="8">Пока нет сохраненных заявок.</td></tr>'
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
        <a href="/index.html">Главная</a>
        <a href="/request.html">Заявка</a>
        <a class="active" href="/admin/requests">Заявки</a>
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
