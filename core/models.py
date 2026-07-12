from datetime import datetime, time
from decimal import Decimal

from django.db import models, transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Branch(TimeStampedModel):
    name = models.CharField(max_length=120)
    location = models.CharField(max_length=160)
    manager_name = models.CharField(max_length=120)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Supplier(TimeStampedModel):
    name = models.CharField(max_length=160)
    contact_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=40)
    email = models.EmailField(blank=True, null=True)
    products_supplied = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

    @property
    def total_paid(self):
        return self.payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    @property
    def total_po_value(self):
        line_total = ExpressionWrapper(
            F('quantity_received') * F('unit_price'),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
        total = (
            PurchaseOrderItem.objects.filter(
                purchase_order__supplier=self,
                purchase_order__status__in=[PurchaseOrder.Status.PARTIALLY_RECEIVED, PurchaseOrder.Status.FULLY_RECEIVED],
            ).aggregate(total=Sum(line_total))['total']
        )
        return total or Decimal('0.00')

    @property
    def outstanding_balance(self):
        return self.total_po_value - self.total_paid


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Product(TimeStampedModel):
    class Unit(models.TextChoices):
        TABLETS = 'tablets', 'tablets'
        BOTTLES = 'bottles', 'bottles'
        PACKS = 'packs', 'packs'
        CARTONS = 'cartons', 'cartons'
        SACHETS = 'sachets', 'sachets'

    name = models.CharField(max_length=160)
    sku = models.CharField(max_length=40, unique=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    unit = models.CharField(max_length=20, choices=Unit.choices)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    reorder_point = models.PositiveIntegerField()

    class Meta:
        ordering = ['name']

    def __str__(self) -> str:
        return f'{self.name} ({self.sku})'


class BranchInventory(TimeStampedModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='inventories')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventories')
    quantity = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['branch', 'product'], name='unique_branch_product_inventory'),
        ]
        ordering = ['branch__name', 'product__name']

    def __str__(self) -> str:
        return f'{self.branch} - {self.product}'

    @property
    def stock_status(self):
        if self.quantity == 0:
            return 'out_of_stock'
        if self.quantity <= self.product.reorder_point:
            return 'low_stock'
        return 'in_stock'


class StockMovement(models.Model):
    class MovementType(models.TextChoices):
        RECEIPT = 'receipt', 'receipt'
        ADJUSTMENT = 'adjustment', 'adjustment'
        TRANSFER_IN = 'transfer_in', 'transfer_in'
        TRANSFER_OUT = 'transfer_out', 'transfer_out'

    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='stock_movements')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    movement_type = models.CharField(max_length=20, choices=MovementType.choices)
    quantity_change = models.IntegerField()
    reference = models.CharField(max_length=120, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.CharField(max_length=120)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self) -> str:
        return f'{self.product} {self.quantity_change:+d}'


class PurchaseOrder(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'draft'
        SENT = 'sent', 'sent'
        PARTIALLY_RECEIVED = 'partially_received', 'partially_received'
        FULLY_RECEIVED = 'fully_received', 'fully_received'
        CANCELLED = 'cancelled', 'cancelled'

    po_number = models.CharField(max_length=20, unique=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.PROTECT, related_name='purchase_orders')
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at', '-id']

    def __str__(self) -> str:
        return self.po_number or 'Draft PO'

    @property
    def total_value(self):
        total = self.items.aggregate(
            total=Sum(ExpressionWrapper(F('quantity_ordered') * F('unit_price'), output_field=DecimalField(max_digits=14, decimal_places=2)))
        )['total']
        return total or Decimal('0.00')

    def save(self, *args, **kwargs):
        if not self.po_number:
            today = timezone.localdate()
            count = PurchaseOrder.objects.filter(created_at__date=today).count() + 1
            self.po_number = f'PO-{today:%Y%m%d}-{count:03d}'
        super().save(*args, **kwargs)


class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='purchase_order_items')
    quantity_ordered = models.PositiveIntegerField()
    quantity_received = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ['id']

    def __str__(self) -> str:
        return f'{self.purchase_order.po_number} - {self.product.name}'

    @property
    def outstanding_quantity(self):
        return max(self.quantity_ordered - self.quantity_received, 0)


class SupplierPayment(TimeStampedModel):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name='payments')
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.SET_NULL, blank=True, null=True, related_name='payments')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_date = models.DateField()
    reference = models.CharField(max_length=120)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-payment_date', '-id']

    def __str__(self) -> str:
        return f'{self.supplier} - {self.amount}'


class DailyReport(TimeStampedModel):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='daily_reports')
    report_date = models.DateField()
    opening_stock_value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    receipts_value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    adjustments_value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    closing_stock_value = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    generated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['branch', 'report_date'], name='unique_branch_report_date'),
        ]
        ordering = ['-report_date', 'branch__name']

    def __str__(self) -> str:
        return f'{self.branch} - {self.report_date}'

    @classmethod
    def generate_for(cls, branch, report_date):
        current_tz = timezone.get_current_timezone()
        start = timezone.make_aware(datetime.combine(report_date, time.min), current_tz)
        end = timezone.make_aware(datetime.combine(report_date, time.max), current_tz)

        report, _ = cls.objects.get_or_create(branch=branch, report_date=report_date)
        opening_stock_value = Decimal('0.00')
        receipts_value = Decimal('0.00')
        adjustments_value = Decimal('0.00')
        closing_stock_value = Decimal('0.00')

        for inventory in branch.inventories.select_related('product'):
            before_total = branch.stock_movements.filter(product=inventory.product, created_at__lt=start).aggregate(
                total=Sum('quantity_change')
            )['total'] or 0
            opening_qty = max(before_total, 0)
            received_qty = branch.stock_movements.filter(
                product=inventory.product,
                movement_type=StockMovement.MovementType.RECEIPT,
                created_at__range=(start, end),
            ).aggregate(total=Sum('quantity_change'))['total'] or 0
            adjusted_qty = branch.stock_movements.filter(
                product=inventory.product,
                movement_type=StockMovement.MovementType.ADJUSTMENT,
                created_at__range=(start, end),
            ).aggregate(total=Sum('quantity_change'))['total'] or 0
            closing_qty = opening_qty + received_qty + adjusted_qty
            price = inventory.product.unit_price
            opening_stock_value += Decimal(opening_qty) * price
            receipts_value += Decimal(received_qty) * price
            adjustments_value += Decimal(adjusted_qty) * price
            closing_stock_value += Decimal(closing_qty) * price

            DailyReportLine.objects.update_or_create(
                report=report,
                product=inventory.product,
                defaults={
                    'opening_qty': opening_qty,
                    'received_qty': received_qty,
                    'adjusted_qty': adjusted_qty,
                    'closing_qty': closing_qty,
                },
            )

        report.opening_stock_value = opening_stock_value
        report.receipts_value = receipts_value
        report.adjustments_value = adjustments_value
        report.closing_stock_value = closing_stock_value
        report.save(update_fields=['opening_stock_value', 'receipts_value', 'adjustments_value', 'closing_stock_value', 'generated_at'])
        return report


class DailyReportLine(models.Model):
    report = models.ForeignKey(DailyReport, on_delete=models.CASCADE, related_name='lines')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='daily_report_lines')
    opening_qty = models.IntegerField()
    received_qty = models.IntegerField()
    adjusted_qty = models.IntegerField()
    closing_qty = models.IntegerField()

    class Meta:
        ordering = ['product__name']

    def __str__(self) -> str:
        return f'{self.report} - {self.product}'
