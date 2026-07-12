1. One-line description — Branch-level inventory, purchase order, supplier payment, and stock health tracking for multi-branch retail operations.

2. Live demo link and one screenshot or GIF of the most interesting screen

Live demo: https://example.com

![Dashboard screenshot](docs/dashboard.png)

3. The problem — 2–3 sentences on the real-world pain this solves, written from the user's perspective not the developer's

I need a single view of branch stock health, open purchase orders, and supplier exposure without flipping between spreadsheets and email threads.
When a branch runs low on stock I need a fast way to turn that into a PO, confirm receipts, and keep supplier balances accurate.
This eliminates manual reconciliation of branch inventories, purchase orders, and payment liability.

4. Architecture overview — explain the key technical decisions and why they were made. For example: why multi-tenancy was implemented at the schema level rather than row level, or why Celery was chosen for webhook processing instead of synchronous handling. This section should read like a decision log, not a feature list.

This is a single-schema Django application with normalized branch, product, PO, inventory, and payment tables. I kept scope-level isolation at the application model layer instead of row-level tenant filtering because the system is designed for one business with multiple branches, not multi-tenant SaaS. That simplifies queries and avoids introducing tenant-ID middleware across every model.

I chose server-rendered Django templates over a JS frontend because the product is operational tooling for back-office users and reducing UI complexity shortens delivery. Form handling, PO creation, receipt confirmation, and inventory status are all implemented in the request/response cycle.

Static files are served with Whitenoise inside a container to keep deployment simple. Gunicorn is the WSGI server for Northflank container compatibility because it is stable, easy to configure, and avoids the extra layer of uWSGI config.

Daily report generation uses explicit aggregation logic in the model layer instead of relying on a separate reporting pipeline. That decision preserves consistency between live inventory state and report values while the current load is small enough for on-demand generation.

5. Tech stack — list each technology with one sentence explaining why it was chosen over the obvious alternative. Not just 'Django' — 'Django because the ORM's annotation system allowed complex tenant-scoped aggregations without raw SQL.'

- Python 3.12: chosen for current Django support and consistent container runtime behavior.
- Django: chosen for its ORM and built-in admin, which let me express branch/product/PO aggregations without raw SQL and ship a working operations UI quickly.
- Gunicorn: chosen over Windows-native servers because it is the standard WSGI process manager for Linux containers and works cleanly on Northflank.
- Whitenoise: chosen over separate static hosting because it keeps the container self-contained and avoids extra CDN configuration for the initial deployment.
- SQLite: chosen for local development and demo deployment because it requires no external database service, with a clear path to PostgreSQL later.

6. Local setup — minimal, copy-pasteable, no unnecessary explanation

python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

7. Key engineering challenges — 2–3 specific hard problems encountered and how they were solved. Be specific: not 'I handled webhooks' but 'Paystack occasionally sends duplicate webhook events; I solved this with idempotency keys stored in Redis with a 24-hour TTL, preventing double charges on retried deliveries.'

- Supplier outstanding balance needed to include received PO line values and supplier payments without multiple Python loops, so I implemented `Supplier.total_po_value` with ORM `ExpressionWrapper` and `Sum` to compute the aggregate in the database.
- Receipt processing had to update inventory, stock movement history, and PO status atomically, so I wrapped the POST handler in `transaction.atomic()` and limited `quantity_received` with a `min(..., quantity_ordered)` guard.
- Branch inventory health needed a worst-case stock status across products and branches, so I pre-fetched related branch and product rows and computed inventory status in Python after filtering, instead of issuing one query per branch/product pair.

8. What's next — 2–3 honest next steps, not a fantasy roadmap

- Replace SQLite with PostgreSQL for production and add migration testing for report queries.
- Add authentication and role-based access for purchasing, receiving, and supplier payment functions.
- Move daily report generation to a background job if report workload grows beyond on-demand aggregation.

9. Author line — Divine Agbah, link to Twitter/X and LinkedIn

Divine Agbah — https://twitter.com/divineagbah — https://linkedin.com/in/divineagbah
