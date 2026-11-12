# STEM Books Store

Online store for science (STEM) books, built with **Django** and **Django REST Framework**.
Final project of the Python course.

## Features

- Home page with book cards (cover, title, price, rating, "Add to cart")
- Search by title and filters: category, subcategory, publisher, price range, rating, language; sorting and pagination
- Book page with **Details** and **Review** tabs, rating modal (stars, name, text), similar books and other books by the author
- Cart without registration (stored in the session): change quantity, remove, automatic total
- Discounts, stock control, delivery fee (5 ₾ in Tbilisi, 10 ₾ outside) and estimated delivery date
- Checkout form: the order is saved and can be managed in the admin panel
- Dark / light mode
- REST API under `/api/`

## Setup (virtual environment)

The project uses its own virtual environment (`.venv`). All dependencies are listed in `requirements.txt`.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # admin account for /admin/
python manage.py runserver
```

Open:

- Store: http://127.0.0.1:8000/
- Admin panel: http://127.0.0.1:8000/admin/
- API: http://127.0.0.1:8000/api/

The repository already contains the database (`db.sqlite3`) with the books and the cover images (`media/`).
To load the books into an empty database: `python import_books.py books.txt`.

## Project structure

| Path | Purpose |
|---|---|
| `config/` | project settings and main URLs |
| `shop/models.py` | database models (books, categories, reviews, cart, orders) |
| `shop/web_views.py`, `shop/web_urls.py` | store pages |
| `shop/templates/shop/` | HTML templates (Bootstrap) |
| `shop/filters.py`, `shop/serializers.py`, `shop/views.py`, `shop/urls.py` | REST API |
| `shop/admin.py` | admin panel configuration |
| `import_books.py`, `attach_covers.py`, `set_delivery_dates.py` | helper scripts for loading data |