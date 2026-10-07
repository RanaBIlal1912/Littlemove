# LittleMove store

Online shop for LittleMove kids' developmental toys — *Play. Learn. Grow.*

Built with Django. No paid plugins, no monthly platform fee.

## What it does

**For customers**
- Modern toy-store layout: banner slider, big search, mega menu, mobile bottom bar
- Shop by skill, by need (calm and focus, first words, strong hands…), by age and by budget
- Sale % badges, "You save Rs …", therapist picks, sold-out labels
- Search, sort, product pages with "helps with" and "in the box" lists
- Cart (no account needed), stock checked live
- Checkout with **Cash on delivery, JazzCash, EasyPaisa or bank transfer**
  (prepaid orders ask for the transaction ID from the SMS)
- Free-delivery bar ("add Rs 650 more for free delivery")
- Order confirmation with a one-tap **"Send order on WhatsApp"** button
- Order tracking with order number + mobile number
- Works well on phones; fonts are bundled so it loads fast on mobile data

**For you (admin panel at `/manage-store/`)**
- Add toys with photos, price, old price (shows "Sale"), stock, ages
- Edit price and stock straight from the list; filter sold-out / low stock
- Orders list with colour-coded status; one-click actions:
  confirm → packed → shipped → delivered, mark paid, **cancel and restock**
- "Open WhatsApp chat" link on every order to message the customer
- Courier name and tracking number shown to the customer on the tracking page
- **Banners** for the home slider — upload 1600×600 pictures made in Canva
  (plus an optional 800×800 phone version). Without a picture a coloured banner is shown.
- **Needs** ("Shop by need") — tick which needs each toy suits on the product page
- **Category photos** — optional round photos for the "Shop by skill" circles
- **Testimonials** — paste real messages from parents (with their permission);
  the "What parents say" section appears once you add one
- Top-bar messages: separate several with | and they rotate
- Store settings: WhatsApp number, delivery fee, free-delivery amount,
  JazzCash/EasyPaisa numbers, bank details, top announcement bar
- Optional email alert for each new order

## Run it on your computer

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # then set DEBUG=True in .env for local use

python manage.py migrate
python manage.py seed_store        # 5 categories + 12 sample toys
python manage.py createsuperuser   # your admin login
python manage.py runserver
```

- Shop: http://127.0.0.1:8000
- Admin: http://127.0.0.1:8000/manage-store/

Already running an older copy? After replacing the files run
`python manage.py migrate` and `python manage.py seed_store` once more.

Run the tests with `python manage.py test` (15 tests: checkout, stock, payments, tracking).

## First things to change in the admin

1. **Store settings** — check WhatsApp number, JazzCash/EasyPaisa numbers,
   account title, delivery fee, free-delivery amount. Add bank details only if you
   want bank transfer as an option.
2. **Products** — the sample toys have example prices and stock. Upload real
   square photos (800×800 or bigger); until then a drawing is shown.
3. Delete or hide (untick *Visible in shop*) any sample toy you don't sell.

## Put it online

Any Python host works. Two easy options:

**PythonAnywhere** (simplest, about $5/month for a custom domain)
1. Upload the project (or `git clone` it) and create a virtualenv with `requirements.txt`.
2. Create `.env` from `.env.example`: set `SECRET_KEY`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`.
3. In the Web tab, point WSGI to `config.wsgi`, then run
   `python manage.py migrate`, `python manage.py collectstatic`, `python manage.py createsuperuser`.
4. Add static-file mappings: `/static/` → `staticfiles/`, `/media/` → `media/`
   (then you can set `SERVE_MEDIA=False`).
5. Turn on HTTPS for your domain in the Web tab.

**A VPS (DigitalOcean, Hostinger, etc.)**
Run `gunicorn config.wsgi` behind Nginx, let Nginx serve `/media/`, and use
Let's Encrypt for HTTPS. Set `DATABASE_URL` if you want PostgreSQL
(and uncomment `psycopg` in `requirements.txt`).

**Back up** `db.sqlite3` (or your database) and the `media/` folder regularly — they hold
your orders and product photos.

## Project layout

```
config/      settings and URLs
store/       categories, products, cart, shop pages, store settings
orders/      checkout, orders, tracking, admin order tools, tests
templates/   all page templates
static/      CSS, fonts, favicon
```
