# OpsCore — Product Requirements Document
*Multi-Branch Inventory + Purchase Order System*
*Forté Web Studio · Proof Project v3 · Company-Facing*

---

## AGENT INSTRUCTIONS
Read this entire document before writing a single line of code. Every model, every page, every UI component, every token is defined here. Do not substitute your own judgment on structure, naming, or design. Follow the build order exactly. The demo must work end-to-end with seeded data for 3 branches, 2 suppliers, and 20 products. No login is required for the demo — the admin dashboard opens directly.

---

## 1. What This Is

OpsCore is a multi-branch inventory and purchase order management system for Nigerian mid-size companies — pharmacies, FMCG distributors, retail chains. It replaces the combination of Excel sheets, WhatsApp groups, and memory that operations managers currently use to track stock across branches and manage supplier orders.

**The buyer:** An Operations Manager or CTO at a company with 2–10 branches who is currently losing money to stockouts, expired goods, and supplier payment disputes they cannot track.

**What it replaces:**
- "Check with the Ikeja branch on WhatsApp to see if they have paracetamol"
- "I think we ordered from Emzor last week — check the Excel file"
- "We paid Multipro twice for the same delivery"

---

## 2. Target Demo Business

**Name:** MedCore Pharmacy Group (seeded)
**Branches:** Ikeja branch, Victoria Island branch, Lekki branch
**Suppliers:** Emzor Pharmaceuticals, Multipro Consumer Products
**Products:** 20 pharmaceutical/FMCG products across all branches

---

## 3. Features — v1 Scope

### 3.1 Branch Management
- List all branches with location and manager name
- Each branch has its own inventory, its own purchase orders, and its own daily reports
- Admin sees all branches; branch manager sees their branch only

### 3.2 Product Catalog
- Company-wide product catalog (shared across all branches)
- Each product: name, SKU, category, unit (tablets/bottles/packs), unit price, reorder point
- Products are not branch-specific — stock per branch is tracked in BranchInventory

### 3.3 Inventory (per branch)
- View current stock level per product per branch
- Visual status: In Stock (green) / Low Stock (amber — at or below reorder point) / Out of Stock (red)
- Quick stock adjustment — manual correction with reason (damage / count correction / theft)
- Stock movement history per product (audit log)
- Cross-branch stock view (admin only) — all branches side by side

### 3.4 Purchase Orders
- Create a PO: select branch, select supplier, add line items (product + quantity + agreed price)
- PO statuses: Draft → Sent → Partially Received → Fully Received → Cancelled
- Mark delivery received: confirm quantities received per line item, auto-update BranchInventory
- Partial delivery supported — PO stays open until fully received or cancelled
- PO detail shows: items ordered vs received, outstanding quantities, total value

### 3.5 Supplier Management
- Supplier profile: name, contact, products typically supplied
- Supplier ledger: all POs raised to this supplier, total value ordered, total paid
- Record payment against a supplier: amount, date, reference, linked PO (optional)
- Outstanding balance: total PO value minus total payments recorded

### 3.6 Daily Closing Report (per branch)
- Generated per branch per day
- Shows: opening stock (previous day's closing), stock received via POs today, manual adjustments today, closing stock
- Accessible by date — select any past date to view historical report
- Admin can view reports for all branches

### 3.7 Admin Dashboard (home screen)
- Total stock value across all branches
- Low stock alerts across all branches (product name, branch, current qty, reorder point)
- Active purchase orders (status and value)
- Supplier payments due this week (POs received but unpaid)
- Branch-by-branch stock health summary (how many products In Stock / Low / Out)

---

## 4. Out of Scope for v1
- Point of sale / sales tracking (this is a procurement and inventory tool, not a sales tool)
- Customer management
- Paystack or payment gateway integration
- Mobile app
- Email notifications
- Multi-company / SaaS multi-tenancy
- Barcode scanning
- Accounting software integration

---

## 5. Data Models

```python
# Branch
id, name (str), location (str), manager_name (str), created_at

# Supplier
id, name (str), contact_name (str), phone (str), email (str, nullable),
products_supplied (text, nullable), created_at

# Category
id, name (str)
# Seed: Analgesics, Antibiotics, Vitamins, Personal Care, Household

# Product (company-wide catalog)
id, name (str), sku (str, unique), category (FK → Category),
unit (str — tablets/bottles/packs/cartons/sachets),
unit_price (decimal), reorder_point (int), created_at

# BranchInventory (stock level per product per branch)
id, branch (FK → Branch), product (FK → Product),
quantity (int, default 0), last_updated (datetime)
# Unique together: (branch, product)

# StockMovement (immutable audit log — never update, only insert)
id, branch (FK → Branch), product (FK → Product),
movement_type (receipt / adjustment / transfer_in / transfer_out),
quantity_change (int — positive or negative),
reference (str, nullable — PO number or adjustment reason),
notes (text, nullable), created_at, created_by (str)

# PurchaseOrder
id, po_number (str, auto-generated: PO-YYYYMMDD-NNN),
branch (FK → Branch), supplier (FK → Supplier),
status (draft / sent / partially_received / fully_received / cancelled),
notes (text, nullable), created_at, updated_at

# PurchaseOrderItem
id, purchase_order (FK → PurchaseOrder),
product (FK → Product), quantity_ordered (int),
quantity_received (int, default 0), unit_price (decimal)
# quantity_received increments with each delivery

# SupplierPayment
id, supplier (FK → Supplier), purchase_order (FK → PurchaseOrder, nullable),
amount (decimal), payment_date (date), reference (str), notes (text, nullable),
created_at

# DailyReport (snapshot — generated/regenerated on demand for a given branch+date)
id, branch (FK → Branch), report_date (date),
opening_stock_value (decimal), receipts_value (decimal),
adjustments_value (decimal), closing_stock_value (decimal),
generated_at (datetime)
# Unique together: (branch, report_date)

# DailyReportLine (line items inside a DailyReport)
id, report (FK → DailyReport), product (FK → Product),
opening_qty (int), received_qty (int), adjusted_qty (int), closing_qty (int)
```

---

## 6. URL Structure

```
/                           → Admin Dashboard (redirect here on load)
/branches/                  → Branch list
/branches/<id>/             → Branch detail + inventory for that branch
/products/                  → Product catalog
/products/<id>/             → Product detail + stock across branches + movement history
/inventory/                 → Cross-branch inventory table (admin view)
/purchase-orders/           → PO list (filterable by status and branch)
/purchase-orders/create/    → Create new PO
/purchase-orders/<id>/      → PO detail + receive delivery form
/suppliers/                 → Supplier list
/suppliers/<id>/            → Supplier profile + ledger + payment form
/reports/                   → Daily report index
/reports/<branch_id>/<date>/→ Daily report for branch on date
/adjustments/create/        → Manual stock adjustment form
```

---

## 7. Design Token System

**Visual direction: Enterprise Minimal. Inspired by Linear.app.**
This is daily-use operations software for an Operations Manager, not a consumer app or a marketing site. It must feel serious, data-dense, and immediately trustworthy. The person opening this needs to scan 50 products across 3 branches in under 30 seconds.

**[NON-NEGOTIABLE] Agent must define these as CSS custom properties and use them exclusively:**

```css
:root {
  /* Layout */
  --sidebar-bg: #111827;
  --sidebar-text: #9CA3AF;
  --sidebar-text-active: #FFFFFF;
  --sidebar-accent-bar: #2563EB;

  /* Content */
  --content-bg: #F9FAFB;
  --card-bg: #FFFFFF;
  --border: #E5E7EB;
  --border-strong: #D1D5DB;

  /* Text */
  --text-primary: #111827;
  --text-secondary: #6B7280;
  --text-muted: #9CA3AF;

  /* Actions */
  --action-primary: #2563EB;
  --action-primary-hover: #1D4ED8;
  --action-primary-text: #FFFFFF;

  /* Status */
  --status-success: #059669;
  --status-success-bg: #D1FAE5;
  --status-warning: #D97706;
  --status-warning-bg: #FEF3C7;
  --status-danger: #DC2626;
  --status-danger-bg: #FEE2E2;
  --status-neutral: #6B7280;
  --status-neutral-bg: #F3F4F6;

  /* Spacing */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-5: 20px;
  --space-6: 24px;
  --space-8: 32px;
  --space-10: 40px;
  --space-12: 48px;

  /* Radius — minimal, enterprise */
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
}
```

**Typography:**
```
Font: Inter (Google Fonts) — used for everything
Numbers/codes: JetBrains Mono (PO numbers, SKUs, quantities, currency amounts)
Scale: 12px (labels) / 13px (table rows) / 14px (body) / 16px (section heads) / 20px (page title) / 24px (metric numbers in cards)
Weight: 400 (body) / 500 (table headers, labels) / 600 (page titles, metric numbers)
```

---

## 8. Layout Specification

**Fixed sidebar layout — NOT a top nav.**

```
┌──────────────┬────────────────────────────────────────────┐
│              │  Page Title              [Action Button]   │
│   SIDEBAR    ├────────────────────────────────────────────┤
│   240px      │                                            │
│   fixed      │         MAIN CONTENT AREA                 │
│   #111827    │         background: var(--content-bg)     │
│              │         padding: 24px 32px                 │
│  Logo top    │                                            │
│  Nav items   │                                            │
│  (icons +    │                                            │
│   labels)    │                                            │
└──────────────┴────────────────────────────────────────────┘
```

**Sidebar nav items (in order):**
- Dashboard (grid icon)
- Inventory (package icon)
- Purchase Orders (file-text icon)
- Suppliers (truck icon)
- Products (tag icon)
- Branches (building icon)
- Reports (bar-chart icon)

Active state: left border 3px solid var(--sidebar-accent-bar), text white, background rgba(255,255,255,0.05)

**Icons:** Use Lucide icons via CDN — https://unpkg.com/lucide@latest/dist/umd/lucide.min.js

---

## 9. Component Specifications

### Metric Cards (Dashboard)
```
4 cards in a row, equal width
Background: var(--card-bg)
Border: 1px solid var(--border)
Border radius: var(--radius-lg)
Padding: 20px 24px
Box shadow: 0 1px 3px rgba(0,0,0,0.08)

Contents (top to bottom):
- Label: 12px, Inter 500, var(--text-secondary), uppercase, letter-spacing 0.05em
- Value: 24px, Inter 600, var(--text-primary), JetBrains Mono for numbers
- Trend or sub-label: 13px, var(--text-muted)
```

### Data Tables (all list views)
```
Full width, border-collapse
Header row: background var(--content-bg), 13px Inter 500, var(--text-secondary),
            uppercase, letter-spacing 0.03em, border-bottom 2px solid var(--border-strong)
Body rows: 13px Inter 400, var(--text-primary), row height 44px minimum
           border-bottom 1px solid var(--border)
           hover: background #F9FAFB
Alternating rows: do NOT use — hover is enough
Numbers/codes: JetBrains Mono
```

### Status Badges (THE signature visual element)
```
Display: inline-flex, align-items center, gap 6px
Padding: 2px 8px
Border radius: var(--radius-sm) — not pills, slightly rounded rectangles
Font: 12px Inter 500 uppercase
A small colored dot (6px circle) before the label

In Stock:          dot + text, color var(--status-success), bg var(--status-success-bg)
Low Stock:         dot + text, color var(--status-warning), bg var(--status-warning-bg)
Out of Stock:      dot + text, color var(--status-danger),  bg var(--status-danger-bg)
Draft (PO):        dot + text, color var(--status-neutral), bg var(--status-neutral-bg)
Sent (PO):         dot + text, color var(--status-warning), bg var(--status-warning-bg)
Partially Received:dot + text, color var(--action-primary), bg #DBEAFE
Fully Received:    dot + text, color var(--status-success), bg var(--status-success-bg)
Cancelled:         dot + text, color var(--status-danger),  bg var(--status-danger-bg)
```

### Action Buttons
```
Primary: background var(--action-primary), text white, border none,
         padding 8px 16px, radius var(--radius-md), 14px Inter 500
         hover: var(--action-primary-hover)
Secondary: background transparent, border 1px solid var(--border-strong),
           text var(--text-primary), same padding/radius
Danger: background var(--status-danger), text white, same padding/radius
```

### Page Header (every page)
```
Flex row, justify-content space-between, align-items center
margin-bottom: var(--space-6)
border-bottom: 1px solid var(--border), padding-bottom: var(--space-5)
Left: page title (20px Inter 600) + optional breadcrumb above (12px, muted)
Right: primary action button
```

### Alert Banner (low stock warnings on dashboard)
```
Background var(--status-warning-bg)
Border-left: 3px solid var(--status-warning)
Padding: 12px 16px
Radius: var(--radius-md)
Text: 13px Inter, var(--text-primary)
Icon: warning triangle, var(--status-warning), 16px, left of text
```

---

## 10. Page-by-Page Specifications

### Dashboard (/)
**Metric cards row (4 cards):**
1. Total Stock Value — sum of (BranchInventory.quantity × Product.unit_price) across all branches
2. Low Stock Alerts — count of BranchInventory rows at or below reorder_point
3. Active POs — count of POs with status draft/sent/partially_received
4. Unpaid Supplier Balance — sum of all PO values (fully/partially received) minus all SupplierPayments

**Low Stock Alerts table** (below cards):
Columns: Product, SKU, Branch, Current Qty, Reorder Point, Action (→ Create PO)
Sorted by: most critical first (Out of Stock before Low Stock)

**Active Purchase Orders table:**
Columns: PO Number, Branch, Supplier, Status badge, Total Value, Created Date, Action (→ View)

**Branch Stock Health summary:**
Simple table: Branch name | In Stock count | Low Stock count | Out of Stock count

---

### Inventory (/inventory/)
Admin view — all branches side by side.

**Filters (top bar):** Branch (dropdown, default All), Category (dropdown, default All), Status (All / Low Stock / Out of Stock)

**Table columns:**
Product | SKU | Category | [Branch 1 qty] | [Branch 2 qty] | [Branch 3 qty] | Status (worst status across branches)

Branch quantity columns use status badge colors for the number:
- Green text if above reorder point
- Amber text if at/below reorder point  
- Red text if zero

**Quick action:** Click any cell → inline form to create PO for that branch/product

---

### Branch Detail (/branches/<id>/)
**Header:** Branch name, location, manager name, [Create PO for this branch] button

**Inventory table for this branch:**
Columns: Product | SKU | Category | Qty | Reorder Point | Status | Last Updated | Actions (Adjust)

**Recent stock movements (last 20):**
Columns: Date | Product | Type | Change (±qty in JetBrains Mono) | Reference | Notes

---

### Purchase Orders (/purchase-orders/)
**Filters:** Status (tab bar: All / Draft / Sent / In Progress / Completed) | Branch | Supplier | Date range

**Table columns:**
PO Number | Branch | Supplier | Status | Items | Total Value | Created | Last Updated | Actions

**Create PO (/purchase-orders/create/):**
Step 1: Select branch, select supplier
Step 2: Add line items — product search (autocomplete by name or SKU), quantity, unit price
Step 3: Review and save as Draft or Sent

**PO Detail (/purchase-orders/<id>/):**
Header: PO number, status badge, branch, supplier, created date
Line items table: Product | Ordered | Received | Outstanding | Unit Price | Line Total
Status colors on Outstanding column: green if 0, amber if partial, red if nothing received
[Mark Delivery Received] button → form to enter quantities received per item
PO auto-updates status: partially_received if some items done, fully_received when all received

---

### Supplier Detail (/suppliers/<id>/)
**Header:** Supplier name, contact, phone, email

**Ledger section:**
Total PO value (received POs only) | Total Paid | Outstanding Balance (in JetBrains Mono, red if > 0)

**PO History table:** PO Number | Date | Value | Status | Paid Against This PO

**Payment History table:** Date | Amount | Reference | Linked PO | Notes

**[Record Payment] form:** amount, date, reference, optional link to PO, notes

---

### Daily Report (/reports/<branch_id>/<date>/)
**Header:** Branch name — Report for [Date] | [Generate/Refresh] button

**Summary row:** Opening Value | Received Today | Adjustments Today | Closing Value (all in JetBrains Mono)

**Line items table:**
Product | Opening Qty | Received | Adjusted | Closing Qty | Closing Value

---

## 11. Business Logic — Critical Implementations

**Auto-generate PO number:**
```python
def generate_po_number():
    today = date.today().strftime('%Y%m%d')
    count = PurchaseOrder.objects.filter(
        created_at__date=date.today()
    ).count() + 1
    return f"PO-{today}-{count:03d}"
```

**Stock update on delivery receipt:**
```python
# Must run inside transaction.atomic()
def receive_delivery(po_item, quantity_received):
    po_item.quantity_received += quantity_received
    po_item.save()
    
    # Update BranchInventory
    inventory, _ = BranchInventory.objects.get_or_create(
        branch=po_item.purchase_order.branch,
        product=po_item.product,
        defaults={'quantity': 0}
    )
    inventory.quantity += quantity_received
    inventory.last_updated = now()
    inventory.save()
    
    # Write immutable audit row
    StockMovement.objects.create(
        branch=po_item.purchase_order.branch,
        product=po_item.product,
        movement_type='receipt',
        quantity_change=quantity_received,
        reference=po_item.purchase_order.po_number,
        notes=f"Received against {po_item.purchase_order.po_number}"
    )
    
    # Update PO status
    po = po_item.purchase_order
    all_items = po.purchaseorderitem_set.all()
    if all(i.quantity_received >= i.quantity_ordered for i in all_items):
        po.status = 'fully_received'
    else:
        po.status = 'partially_received'
    po.save()
```

**Stock status calculation:**
```python
def get_stock_status(branch_inventory):
    if branch_inventory.quantity == 0:
        return 'out_of_stock'
    elif branch_inventory.quantity <= branch_inventory.product.reorder_point:
        return 'low_stock'
    else:
        return 'in_stock'
```

**Supplier outstanding balance:**
```python
def get_supplier_balance(supplier):
    total_po_value = PurchaseOrderItem.objects.filter(
        purchase_order__supplier=supplier,
        purchase_order__status__in=['partially_received', 'fully_received']
    ).aggregate(
        total=Sum(F('quantity_received') * F('unit_price'))
    )['total'] or 0
    
    total_paid = SupplierPayment.objects.filter(
        supplier=supplier
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    return total_po_value - total_paid
```

---

## 12. Seed Data (management command: `python manage.py seed_demo`)

```
3 Branches: Ikeja, Victoria Island, Lekki
2 Suppliers: Emzor Pharmaceuticals, Multipro Consumer Products
5 Categories: Analgesics, Antibiotics, Vitamins, Personal Care, Household
20 Products across categories with realistic Nigerian pharma/FMCG names and prices
BranchInventory: randomised quantities — some in stock, some low, some out
3 POs in various statuses: 1 draft, 1 partially received, 1 fully received
2 SupplierPayments: one full payment, one partial (leaving outstanding balance)
5 days of StockMovements (realistic history)
1 DailyReport per branch for yesterday
```

---

## 13. Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | Django 4.2 LTS | ORM handles all aggregations cleanly; F() expressions for stock math |
| Frontend | Django templates + Bootstrap 5 + HTMX | No JavaScript framework overhead; HTMX handles inline forms |
| Icons | Lucide (CDN) | Consistent enterprise-grade icon set, zero config |
| Database | SQLite (demo) | No infrastructure needed for PythonAnywhere free tier |
| Charts | Chart.js (CDN) | One small chart on dashboard; no install needed |
| Fonts | Google Fonts (Inter + JetBrains Mono) | Load both in base template |

---

## 14. Build Order

**Phase 1 — Models and Admin**
1. Project setup, app structure
2. All models from Section 5, exactly as specified
3. Django admin registration for all models (for seeding)
4. `seed_demo` management command
5. Base template: sidebar layout, CSS custom properties, Inter + JetBrains Mono loaded

**Phase 2 — Core Views**
1. Dashboard view with all four metric queries
2. Inventory list view (cross-branch table)
3. Branch detail view
4. Product catalog and detail view

**Phase 3 — Purchase Orders**
1. PO list view with status filters
2. PO create view with product autocomplete (HTMX)
3. PO detail view
4. Receive delivery form with `receive_delivery` logic from Section 11

**Phase 4 — Suppliers**
1. Supplier list view
2. Supplier detail with ledger calculations from Section 11
3. Record payment form

**Phase 5 — Reports + Polish**
1. Daily report generation view
2. Report line items calculation
3. Manual stock adjustment form
4. Status badges applied consistently per Section 9
5. Alert banners for low stock on dashboard
6. Mobile responsiveness (sidebar collapses to hamburger on mobile)

---

## 15. Deployment — PythonAnywhere Free Tier

Same as StudioFlow. SQLite, always-on, no spindown.

**Build command:** `pip install -r requirements.txt && python manage.py migrate && python manage.py seed_demo`
**Start:** point PythonAnywhere Web App to `opscore/wsgi.py`

**Environment variables:**
```
SECRET_KEY=
DEBUG=False
ALLOWED_HOSTS=yourusername.pythonanywhere.com
```

---

## 16. Demo Script (for LinkedIn / company buyer conversations)

1. Open dashboard — show 4 metric cards: total stock value, low stock count, active POs, unpaid balance
2. Click Low Stock Alerts — show Lekki branch is out of Paracetamol 500mg
3. Click "Create PO" from the alert row — show pre-filled PO form for Lekki + Emzor
4. Submit PO, show it appears in Active POs with status "Sent"
5. Go to Suppliers → Emzor — show outstanding balance in red (JetBrains Mono)
6. Record a partial payment — show balance update
7. Go to Reports → Ikeja → yesterday — show daily closing report
*Total demo time: 90 seconds*
*Opening line for the post: "Nigerian companies track millions in inventory across branches on WhatsApp and Excel. Here's what replacing that actually looks like."*
