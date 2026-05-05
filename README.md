# Praktica3kyrs

Сайт ювелирной мастерской для практики.

## Статическая версия

HTML-страницы можно открыть напрямую через `index.html`.

## Версия с обработкой заявок

Для сохранения заявок используется Flask и SQLite.

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

После запуска:

- сайт: `http://127.0.0.1:5000/`
- форма заявки: `http://127.0.0.1:5000/request.html`
- просмотр заявок: `http://127.0.0.1:5000/admin/requests`

Админка открывается через простой вход: `http://127.0.0.1:5000/admin/login`.
Учебный пароль по умолчанию: `admin`.
