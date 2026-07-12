from datetime import date

from django import forms
from django.db import transaction
from django.db.models import F, Q
from django.http import HttpResponseBadRequest
from django.utils.dateparse import parse_date
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

from .forms import PurchaseOrderLineFormSet, PurchaseOrderMetaForm, StockAdjustmentForm, SupplierPaymentForm
from .models import Branch, BranchInventory, DailyReport, Product, PurchaseOrder, PurchaseOrderItem, StockMovement, Supplier, SupplierPayment


def dashboard(request):
    inventories = BranchInventory.objects.select_related('branch', 'product')
    low_stock_alerts = inventories.filter(quantity__lte=F('product__reorder_point')).order_by('quantity', 'branch__name', 'product__name')
    active_pos = PurchaseOrder.objects.select_related('branch', 'supplier').filter(status__in=[
        PurchaseOrder.Status.DRAFT,
        PurchaseOrder.Status.SENT,
        PurchaseOrder.Status.PARTIALLY_RECEIVED,
    ])

    context = {
        'total_stock_value': sum(inv.quantity * inv.product.unit_price for inv in inventories),
        'low_stock_count': low_stock_alerts.count(),
        'active_po_count': active_pos.count(),
        'unpaid_supplier_balance': sum((supplier.outstanding_balance for supplier in Supplier.objects.all()), start=0),
        'low_stock_alerts': low_stock_alerts.select_related('branch', 'product')[:10],
        'active_pos': active_pos[:10],
        'branch_health': [
            {
                'branch': branch,
                'in_stock': branch.inventories.select_related('product').filter(quantity__gt=F('product__reorder_point')).count(),
                'low_stock': branch.inventories.select_related('product').filter(quantity__gt=0, quantity__lte=F('product__reorder_point')).count(),
                'out_of_stock': branch.inventories.filter(quantity=0).count(),
            }
            for branch in Branch.objects.all()
        ],
    }
    return render(request, 'core/dashboard.html', context)


def branches_list(request):
    return render(request, 'core/branches_list.html', {'branches': Branch.objects.all()})


def branch_detail(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    inventories = branch.inventories.select_related('product', 'product__category')
    movements = branch.stock_movements.select_related('product')[:20]
    return render(request, 'core/branch_detail.html', {'branch': branch, 'inventories': inventories, 'movements': movements})


def products_list(request):
    products = Product.objects.select_related('category')
    return render(request, 'core/products_list.html', {'products': products})


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related('category'), pk=pk)
    branch_rows = BranchInventory.objects.filter(product=product).select_related('branch').order_by('branch__name')
    movements = StockMovement.objects.filter(product=product).select_related('branch').order_by('-created_at')[:20]
    return render(request, 'core/product_detail.html', {'product': product, 'branch_rows': branch_rows, 'movements': movements})


def inventory_view(request):
    branches = list(Branch.objects.all())
    category_id = request.GET.get('category')
    branch_id = request.GET.get('branch')
    status_filter = request.GET.get('status', 'all')
    rows = []
    products_qs = Product.objects.select_related('category')
    if category_id:
        products_qs = products_qs.filter(category_id=category_id)
    for product in products_qs:
        inventories = {inv.branch_id: inv for inv in product.inventories.select_related('branch')}
        statuses = [inventories[branch.id].stock_status for branch in branches if branch.id in inventories]
        if 'out_of_stock' in statuses:
            worst_status = 'out_of_stock'
        elif 'low_stock' in statuses:
            worst_status = 'low_stock'
        else:
            worst_status = 'in_stock'
        if branch_id:
            branch_inventory = inventories.get(int(branch_id))
            if branch_inventory is None:
                continue
            worst_status = branch_inventory.stock_status
        if status_filter != 'all' and worst_status != status_filter:
            continue
        rows.append({
            'product_id': product.id,
            'product_name': product.name,
            'product_sku': product.sku,
            'product_category': product.category.name,
            'reorder_point': product.reorder_point,
            'inventories': inventories,
            'worst_status': worst_status,
        })
    return render(
        request,
        'core/inventory_list.html',
        {
            'branches': branches,
            'products': rows,
            'categories': list(Product.objects.values_list('category_id', 'category__name').distinct().order_by('category__name')),
            'filters': {'branch': branch_id or '', 'category': category_id or '', 'status': status_filter},
        },
    )


def purchase_orders_list(request):
    status = request.GET.get('status')
    orders = PurchaseOrder.objects.select_related('branch', 'supplier').prefetch_related('items__product')
    if status and status != 'all':
        if status == 'in_progress':
            orders = orders.filter(status__in=[PurchaseOrder.Status.DRAFT, PurchaseOrder.Status.SENT, PurchaseOrder.Status.PARTIALLY_RECEIVED])
        elif status == 'completed':
            orders = orders.filter(status__in=[PurchaseOrder.Status.FULLY_RECEIVED, PurchaseOrder.Status.CANCELLED])
        else:
            orders = orders.filter(status=status)
    branch_id = request.GET.get('branch')
    if branch_id:
        orders = orders.filter(branch_id=branch_id)
    supplier_id = request.GET.get('supplier')
    if supplier_id:
        orders = orders.filter(supplier_id=supplier_id)
    date_from = parse_date(request.GET.get('from') or '')
    date_to = parse_date(request.GET.get('to') or '')
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    return render(
        request,
        'core/purchase_orders_list.html',
        {
            'orders': orders,
            'branches': Branch.objects.all(),
            'suppliers': Supplier.objects.all(),
            'active_status': status or 'all',
            'filters': {'branch': branch_id or '', 'supplier': supplier_id or '', 'from': request.GET.get('from', ''), 'to': request.GET.get('to', '')},
        },
    )


@transaction.atomic
def purchase_order_create(request):
    initial_meta = {}
    initial_lines = []
    branch_id = request.GET.get('branch')
    product_id = request.GET.get('product')
    supplier_id = request.GET.get('supplier')
    if branch_id:
        initial_meta['branch'] = branch_id
    if supplier_id:
        initial_meta['supplier'] = supplier_id
    if product_id:
        product = Product.objects.filter(pk=product_id).first()
        initial_lines.append({'product_id': product_id, 'product_query': product.name if product else '', 'quantity_ordered': 1, 'unit_price': product.unit_price if product else 0})
    if request.method == 'POST':
        meta_form = PurchaseOrderMetaForm(request.POST)
        line_formset = PurchaseOrderLineFormSet(request.POST)
        if meta_form.is_valid() and line_formset.is_valid():
            po = PurchaseOrder.objects.create(
                branch=meta_form.cleaned_data['branch'],
                supplier=meta_form.cleaned_data['supplier'],
                status=meta_form.cleaned_data['status'],
                notes=meta_form.cleaned_data['notes'],
            )
            created_any = False
            for form in line_formset:
                if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                    continue
                product = form.cleaned_data.get('product')
                if product is None:
                    continue
                PurchaseOrderItem.objects.create(
                    purchase_order=po,
                    product=product,
                    quantity_ordered=form.cleaned_data['quantity_ordered'],
                    unit_price=form.cleaned_data['unit_price'],
                )
                created_any = True
            if not created_any:
                po.delete()
                return HttpResponseBadRequest('At least one line item is required.')
            return redirect('purchase_order_detail', pk=po.pk)
    else:
        meta_form = PurchaseOrderMetaForm(initial=initial_meta)
        line_formset = PurchaseOrderLineFormSet(initial=initial_lines)
    return render(request, 'core/purchase_order_form.html', {'meta_form': meta_form, 'line_formset': line_formset})


@transaction.atomic
def purchase_order_detail(request, pk):
    po = get_object_or_404(PurchaseOrder.objects.select_related('branch', 'supplier').prefetch_related('items__product'), pk=pk)
    if request.method == 'POST':
        for item in po.items.select_related('product'):
            raw_value = request.POST.get(f'received_{item.pk}')
            if raw_value in (None, ''):
                continue
            received = max(int(raw_value), 0)
            if received <= 0:
                continue
            item.quantity_received = min(item.quantity_received + received, item.quantity_ordered)
            item.save(update_fields=['quantity_received'])
            inventory, _ = BranchInventory.objects.get_or_create(branch=po.branch, product=item.product, defaults={'quantity': 0})
            inventory.quantity += received
            inventory.save(update_fields=['quantity', 'last_updated', 'updated_at'])
            StockMovement.objects.create(
                branch=po.branch,
                product=item.product,
                movement_type=StockMovement.MovementType.RECEIPT,
                quantity_change=received,
                reference=po.po_number,
                notes=f'Received against {po.po_number}',
                created_by='Admin',
            )
        if all(i.quantity_received >= i.quantity_ordered for i in po.items.all()):
            po.status = PurchaseOrder.Status.FULLY_RECEIVED
        elif any(i.quantity_received > 0 for i in po.items.all()):
            po.status = PurchaseOrder.Status.PARTIALLY_RECEIVED
        po.save(update_fields=['status', 'updated_at'])
        return redirect('purchase_order_detail', pk=po.pk)

    return render(request, 'core/purchase_order_detail.html', {'po': po})


def suppliers_list(request):
    return render(request, 'core/suppliers_list.html', {'suppliers': Supplier.objects.all()})


def supplier_detail(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    payments = supplier.payments.select_related('purchase_order')
    po_history = supplier.purchase_orders.select_related('branch').prefetch_related('items__product')
    if request.method == 'POST':
        form = SupplierPaymentForm(request.POST)
        if form.is_valid():
            payment = SupplierPayment.objects.create(
                supplier=form.cleaned_data['supplier'],
                purchase_order=form.cleaned_data['purchase_order'],
                amount=form.cleaned_data['amount'],
                payment_date=form.cleaned_data['payment_date'],
                reference=form.cleaned_data['reference'],
                notes=form.cleaned_data['notes'],
            )
            return redirect('supplier_detail', pk=payment.supplier_id)
    else:
        form = SupplierPaymentForm(initial={'supplier': supplier})
        form.fields['supplier'].widget = forms.HiddenInput()  # type: ignore[name-defined]
    return render(request, 'core/supplier_detail.html', {'supplier': supplier, 'payments': payments, 'po_history': po_history, 'form': form})


@transaction.atomic
def adjustment_create(request):
    if request.method == 'POST':
        form = StockAdjustmentForm(request.POST)
        if form.is_valid():
            branch = form.cleaned_data['branch']
            product = form.cleaned_data['product']
            qty = form.cleaned_data['quantity_change']
            inventory, _ = BranchInventory.objects.get_or_create(branch=branch, product=product, defaults={'quantity': 0})
            inventory.quantity += qty
            inventory.save(update_fields=['quantity', 'last_updated', 'updated_at'])
            StockMovement.objects.create(
                branch=branch,
                product=product,
                movement_type=StockMovement.MovementType.ADJUSTMENT,
                quantity_change=qty,
                reference=form.cleaned_data['reason'],
                notes=form.cleaned_data['notes'],
                created_by=form.cleaned_data['created_by'],
            )
            return redirect('branch_detail', pk=branch.pk)
    else:
        form = StockAdjustmentForm()
    return render(request, 'core/adjustment_form.html', {'form': form})


def reports_detail(request, branch_id, report_date):
    branch = get_object_or_404(Branch, pk=branch_id)
    report_day = date.fromisoformat(report_date)
    if request.method == 'POST':
        report = DailyReport.generate_for(branch, report_day)
    else:
        report = DailyReport.objects.filter(branch=branch, report_date=report_day).prefetch_related('lines__product').first()
        if report is None:
            report = DailyReport.generate_for(branch, report_day)
    return render(request, 'core/report_detail.html', {'branch': branch, 'report': report})


def reports_index(request):
    reports = DailyReport.objects.select_related('branch').order_by('-report_date', 'branch__name')
    return render(request, 'core/reports_index.html', {'reports': reports, 'branches': Branch.objects.all()})


@require_GET
def product_search(request):
    query = (request.GET.get('q') or request.GET.get('product_query') or '').strip()
    prefix = request.GET.get('prefix', '')
    products = Product.objects.select_related('category')
    if query:
        products = products.filter(Q(name__icontains=query) | Q(sku__icontains=query))
    products = products.order_by('name')[:8]
    return render(request, 'core/partials/product_suggestions.html', {'products': products, 'prefix': prefix, 'query': query})
