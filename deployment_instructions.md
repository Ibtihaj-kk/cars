## cPanel / Live Server Deployment Instructions

### 1. Initial setup on the server
- Upload the project to your cPanel account (e.g. into `~/carsyncro`).
- Ensure Python 3.9+ is available and create a virtual environment:
  - `python3 -m venv venv`
  - `source venv/bin/activate` (or `venv\Scripts\activate` on Windows shell)
- Install dependencies:
  - `pip install -r requirements.txt`

### 2. Environment and Django configuration
- Set `DJANGO_SETTINGS_MODULE=yallamotor_project.settings`.
- Configure a `.env` file with database, email, Redis, and other production settings (same keys as in README).
- In cPanel, point your Python application or WSGI configuration to the `yallamotor_project.wsgi:application`.

### 3. Database migrations
- From the project root:
  - `python manage.py migrate`

### 4. Populate currencies and exchange rates
Run the following in order (from project root, with virtualenv active):
- Load currencies (creates USD base + SAR, AED, etc.):
  - `python manage.py loaddata core/fixtures/currencies.json`
- Create initial exchange rates (USD → SAR/AED/QAR/OMR/BHD/PKR):
  - `python manage.py setup_exchange_rates`

Verification:
- Open Django shell:
  - `python manage.py shell`
- Check currencies:
  - `from core.models import Currency, ExchangeRate`
  - `Currency.objects.all()` (ensure USD and SAR exist, USD has `is_base=True`)
  - `ExchangeRate.objects.filter(base_currency__code='USD')` (ensure SAR, AED etc. have active rates)

If `setup_exchange_rates` prints an error about missing USD base currency, it means `currencies.json` was not loaded correctly; re-run the `loaddata` step and then rerun `setup_exchange_rates`.

### 5. Populate countries and cities
There are two helper scripts that use `yallamotor_project.settings` and `django.setup()`; run them from the project root:

- Create core countries and major cities for the 6 target countries:
  - `python setup_countries_cities.py`
- Populate detailed Saudi Arabia cities and areas:
  - `python populate_locations.py`

These scripts use the `Country`, `City`, and `CityArea` models from `parts.models` and are safe to run multiple times; they use `get_or_create` so duplicates are avoided and existing records may be updated.

Verification:
- In Django shell:
  - `from parts.models import Country, City, CityArea`
  - `Country.objects.filter(code='SA')`
  - `City.objects.filter(country__code='SA').count()`
  - `CityArea.objects.count()`

### 6. Collect static files
- `python manage.py collectstatic --noinput`

### 7. Configure cron / scheduled tasks for exchange rates (optional)
Current `setup_exchange_rates` creates initial manual rates and skips currencies that already have an active rate, so it is mainly for initial setup. If you want to periodically refresh rates, you can:

- Either:
  - Implement a separate management command that fetches updated rates from an API and creates new `ExchangeRate` rows (recommended for production).
- Or, if you keep using manual pegs and only occasionally update:
  - Re-run `python manage.py setup_exchange_rates` after clearing or updating existing `ExchangeRate` rows for the affected currencies.

On cPanel, you can add a cron job (for example, daily) to run a custom rate-update command. A typical cron entry (adjust paths and Python binary):
- `0 2 * * * /home/USER/carsyncro/venv/bin/python /home/USER/carsyncro/manage.py your_rate_update_command`

### 8. Common causes of exchange rate issues on live
- `core/fixtures/currencies.json` was not loaded before running `setup_exchange_rates`, so USD or SAR did not exist.
- Migrations were not applied before running the population commands.
- The app was deployed with a different database (e.g. new empty DB) without re-running:
  - `python manage.py loaddata core/fixtures/currencies.json`
  - `python manage.py setup_exchange_rates`
- Environment variables on the live server point to a different database than the one you populated locally or on staging.

To verify live behavior:
- Use Django shell on the live server and run:
  - `from core.models import ExchangeRate`
  - `ExchangeRate.get_current_rate('USD', 'SAR')`
  - `ExchangeRate.get_current_rate('USD', 'AED')`
- If these calls raise `ValueError`, it means the rates were not created; rerun the population commands from Step 4.

