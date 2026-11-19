# PizzaSlice Django backend

The existing storefront is served by Django and uses a PostgreSQL-backed API for the pizza menu, cash-on-delivery orders, and order tracking. Order prices are calculated by the server; prices sent by the browser are not trusted.

## Run locally on Windows

Open PowerShell in this project folder and activate the existing virtual environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install the project's Python dependencies:

```powershell
python -m pip install -r requirements.txt
```

Django is pinned to 5.2 so it works with PostgreSQL 14. If you don't set PostgreSQL environment variables, the project automatically falls back to a local SQLite database so it can run in a development/test setup without a server.

Open the storefront through Django (`http://127.0.0.1:8000/`), not the VS Code Live Server port. The menu and pizza customization pages call the Django API on the same origin.

In pgAdmin, connect to your local PostgreSQL server and run:

```sql
CREATE DATABASE pizzaslice;
```

Back in the same PowerShell window, provide the password you chose for the PostgreSQL `postgres` user. These environment variables apply only to that PowerShell window:

```powershell
$env:POSTGRES_DB = "pizzaslice"
$env:POSTGRES_USER = "postgres"
$env:POSTGRES_PASSWORD = "your-postgres-password"
```

Create the database tables, initial pizza catalog, starter offers, and an admin account:

```powershell
python manage.py migrate
python manage.py createsuperuser
```

In Django admin, add and manage menu categories under **Categories**, then assign each pizza to one of them. Categories with active pizzas appear as filters on the menu automatically. Manage offers under **Deals**. Supported automatic promotion types are fixed-price bundles, fixed-price pairs from a category, and fixed-price individual pizzas, optionally restricted to Tuesday or the weekend. At most one eligible offer is applied per order; automatic promotions require small pizzas, original crust, and no extra toppings. Student verification remains manual. Set each promotion's displayed offer text and its promotion price to the same amount. Checkout gets an authoritative price quote from the server, and orders store their subtotal, applied discount, and final total. Each pizza has editable Small, Medium, Large, and Extra Large prices. The size-price migration preserves the existing small price and carries forward the previous size increments for existing pizzas.

Start Django:

```powershell
python manage.py runserver
```

Open `http://127.0.0.1:8000/` to use the storefront. Use `http://127.0.0.1:8000/admin/` to update pizza availability and order statuses. Keep the same PowerShell window open so the database environment variables remain set.

## API

- `GET /api/pizzas/` — active menu and size prices.
- `GET /api/deals/` — active offers and their display/promotion details.
- `POST /api/orders/quote/` — calculate server-side item prices and applicable offer before checkout.
- `GET /api/pizzas/<slug>/` — one pizza and its customization data.
- `POST /api/orders/` — create a cash-on-delivery order from delivery details and cart items.
- `POST /api/orders/lookup/` — look up an order by its reference and the phone number used at checkout. The tracking page refreshes its status every 15 seconds until it is delivered or cancelled.

The order tracker only returns an order when both the reference and phone number match. Online payment and customer accounts are not included. The built-in frontend file serving is intended for local development with Django's development server, not production deployment.

## Production settings

Before deploying, set `DJANGO_DEBUG=false`, a unique `DJANGO_SECRET_KEY`, and comma-separated `DJANGO_ALLOWED_HOSTS` for custom domains. Vercel deployment and project-production hostnames are included automatically. Set `DJANGO_CSRF_TRUSTED_ORIGINS` to the full trusted HTTPS origins when needed. Use HTTPS and a production static-file server; do not use Django's development server in production.
