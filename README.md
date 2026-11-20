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

Django is pinned to 5.2 and the PostgreSQL driver is included in `requirements.txt`. Local development uses SQLite by default. To use PostgreSQL locally, set all five `DB_*` variables below. Production (including Vercel) requires PostgreSQL configuration and fails with a clear error if any variable is missing.

Open the storefront through Django (`http://127.0.0.1:8000/`), not the VS Code Live Server port. The menu and pizza customization pages call the Django API on the same origin.

In pgAdmin, connect to your local PostgreSQL server and run:

```sql
CREATE DATABASE pizzaslice;
```

Back in the same PowerShell window, provide the connection values for your PostgreSQL database. These environment variables apply only to that PowerShell window:

```powershell
$env:DB_NAME = "pizzaslice"
$env:DB_USER = "postgres"
$env:DB_PASSWORD = "your-postgres-password"
$env:DB_HOST = "127.0.0.1"
$env:DB_PORT = "5432"
```

Create the database tables and initial menu/deal records, then create an admin account:

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

The order tracker only returns an order when both the reference and phone number match. Online payment and customer accounts are not included.

## Static files

The storefront's CSS, images, video, and JavaScript remain in the project root and `js/` directory to preserve the existing layout. `ordering.staticfiles.ProjectRootAssetsFinder` exposes only those asset types to Django's staticfiles system; do not point `STATICFILES_DIRS` at the project root, which could collect source code or local data. The frontend continues to support legacy root-level asset URLs, while pages and API image URLs use `/static/`.

`STATIC_ROOT` is configured as `staticfiles/`. Vercel's Django integration runs `collectstatic` and serves collected files from its CDN, including Django admin assets. The same finder works with Django's local development server. WhiteNoise is not added because Vercel's static CDN handles production delivery.

## Production settings

Before deploying, set `DJANGO_DEBUG=false` and a unique `DJANGO_SECRET_KEY` in Vercel's Environment Variables. Vercel deployment and project-production hostnames are included in `ALLOWED_HOSTS`; their HTTPS origins, including `https://pizza-web-app-six.vercel.app`, are also trusted for CSRF. Set `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_TRUSTED_ORIGINS` to exact hostnames/origins when adding a custom domain. Do not use wildcard hosts or origins. Vercel's forwarded protocol is used for HTTPS detection; Django redirects HTTP to HTTPS, uses secure cookies, and sends an HSTS policy on Vercel. Password validation and Django's default password hashing remain enabled.

For Vercel, configure either all five `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` variables, or a provider-supplied `DATABASE_URL`/`POSTGRES_URL`. The URL must use the `postgres://` or `postgresql://` scheme. Use the values from your managed PostgreSQL provider; do not invent credentials. Configure the environments you deploy (Production and Preview, if used), then redeploy. Keep credentials in Vercel's environment settings, not in source files. Run `python manage.py migrate --noinput` as a controlled release step with the same database configuration; do not run migrations at serverless function startup. Migrations create the schema and initial menu/deal records, but they do not copy existing customer, order, or product records from SQLite. Back up and transfer any existing records separately before switching production traffic to PostgreSQL.
