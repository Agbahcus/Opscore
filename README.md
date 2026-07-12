# OpsCore

Branch inventory, purchase order, supplier payment, and stock health tracking for a multi-branch retail operations team.

## Live demo

Live demo: https://example.com



## Problem

Operations managers need one place to see branch stock health, outstanding supplier obligations, and active purchase orders without switching between spreadsheets, emails, and phone notes.
When a branch hits its reorder point, the team must raise a PO, receive goods, and update inventory without losing the paper trail.
This system removes the manual reconciliation burden and keeps purchase order receipts, supplier payments, and branch inventory aligned.

## Architecture overview

This is a single-schema Django app built for one business with multiple branches. I deliberately avoided tenant middleware and row-level scope filters because the product is not a multi-tenant SaaS platform; that choice keeps model relationships straightforward and avoids introducing tenant keys into every query.

The app uses server-rendered Django templates for click-to-action operations because the target users are back-office staff who need fast, reliable forms rather than a single-page app. That reduces client-side complexity and keeps the deployment footprint smaller.

Inventory and reporting logic live in the model layer, not in a separate analytics pipeline. This means `BranchInventory`, `StockMovement`, `PurchaseOrder`, and `DailyReport` all stay consistent in the same database transaction domain, which is sufficient for the expected workload.

Deployment is container-first with Gunicorn and Whitenoise. I chose that stack because it supports Northflank deployment cleanly and avoids extra reverse-proxy or static-hosting configuration for an initial launch.

## Tech stack

- Python 3.12: current Django support and stable container runtime behavior.
- Django: chosen because the ORM handles inventory, supplier, and PO aggregations without raw SQL and because built-in admin accelerates operational data management.
- Gunicorn: chosen as the standard WSGI server for Linux containers and because it is simpler to configure than uWSGI for this project.
- Whitenoise: chosen over external static hosting so the container can serve static assets directly and keep deployment simple.
- SQLite: chosen for local development and demo deployment because it requires no external database service, with a path to PostgreSQL for production.

## Local setup

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Key engineering challenges

- Supplier exposure needed live PO totals and payment history in a single view, so `Supplier.total_po_value` uses `ExpressionWrapper` and `Sum` to compute committed PO value in the database.
- Receiving goods required updating inventory, writing stock movement history, and changing PO status atomically, so the receipt flow is wrapped in `transaction.atomic()` and each received quantity is capped with `min(..., quantity_ordered)`.
- Branch inventory health needed a worst-case stock status across product/branch intersections without generating one query per cell, so inventory rows are pre-fetched and status is computed in Python per branch-product pair.

## What's next

- Replace SQLite with PostgreSQL for production and add schema migration tests for report queries.
- Add authentication and role-based access controls for purchasing, receiving, and supplier payment actions.
- Move daily report generation to a scheduled background job if report volume exceeds on-demand aggregation performance.

## Author

Divine Agbah — https://twitter.com/divineagbah — https://linkedin.com/in/divineagbah
