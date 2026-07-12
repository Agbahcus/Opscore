from django.contrib import admin

from .models import (
    Branch,
    BranchInventory,
    Category,
    DailyReport,
    DailyReportLine,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    StockMovement,
    Supplier,
    SupplierPayment,
)


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'manager_name', 'created_at')
    search_fields = ('name', 'location', 'manager_name')


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_name', 'phone', 'email')
    search_fields = ('name', 'contact_name', 'phone', 'email')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'unit', 'unit_price', 'reorder_point')
    search_fields = ('name', 'sku')
    list_filter = ('category', 'unit')


@admin.register(BranchInventory)
class BranchInventoryAdmin(admin.ModelAdmin):
    list_display = ('branch', 'product', 'quantity', 'last_updated')
    list_filter = ('branch', 'product__category')
    search_fields = ('branch__name', 'product__name', 'product__sku')


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'branch', 'product', 'movement_type', 'quantity_change', 'reference', 'created_by')
    list_filter = ('movement_type', 'branch')
    search_fields = ('branch__name', 'product__name', 'reference', 'notes')


class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 0


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('po_number', 'branch', 'supplier', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'branch', 'supplier')
    search_fields = ('po_number', 'branch__name', 'supplier__name')
    inlines = [PurchaseOrderItemInline]


@admin.register(SupplierPayment)
class SupplierPaymentAdmin(admin.ModelAdmin):
    list_display = ('supplier', 'purchase_order', 'amount', 'payment_date', 'reference')
    list_filter = ('supplier', 'payment_date')
    search_fields = ('supplier__name', 'reference')


class DailyReportLineInline(admin.TabularInline):
    model = DailyReportLine
    extra = 0


@admin.register(DailyReport)
class DailyReportAdmin(admin.ModelAdmin):
    list_display = ('branch', 'report_date', 'opening_stock_value', 'receipts_value', 'adjustments_value', 'closing_stock_value', 'generated_at')
    list_filter = ('branch', 'report_date')
    inlines = [DailyReportLineInline]
