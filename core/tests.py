from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import BranchInventory, DailyReport, Product, PurchaseOrder, Supplier


class OpsCoreSmokeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)

    def test_primary_routes_render(self):
        routes = [
            reverse('dashboard'),
            reverse('branches_list'),
            reverse('inventory_view'),
            reverse('products_list'),
            reverse('purchase_orders_list'),
            reverse('suppliers_list'),
            reverse('reports_index'),
        ]
        for route in routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)

    def test_detail_routes_render(self):
        product = Product.objects.first()
        branch = product.inventories.first().branch
        po = PurchaseOrder.objects.first()
        supplier = Supplier.objects.first()
        report = DailyReport.objects.first()

        detail_routes = [
            reverse('product_detail', args=[product.pk]),
            reverse('branch_detail', args=[branch.pk]),
            reverse('purchase_order_detail', args=[po.pk]),
            reverse('supplier_detail', args=[supplier.pk]),
            reverse('report_detail', args=[report.branch_id, report.report_date.isoformat()]),
        ]
        for route in detail_routes:
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 200)

    def test_purchase_order_receive_updates_inventory(self):
        po = PurchaseOrder.objects.filter(status__in=[PurchaseOrder.Status.DRAFT, PurchaseOrder.Status.SENT]).first()
        item = po.items.first()
        inventory = BranchInventory.objects.get(branch=po.branch, product=item.product)
        before_qty = inventory.quantity

        response = self.client.post(reverse('purchase_order_detail', args=[po.pk]), {f'received_{item.pk}': 3})
        self.assertEqual(response.status_code, 302)

        inventory.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(inventory.quantity, before_qty + 3)
        self.assertEqual(item.quantity_received, 3)

    def test_supplier_balance_is_decimal(self):
        supplier = Supplier.objects.first()
        self.assertIsInstance(supplier.outstanding_balance, Decimal)

    def test_product_search_endpoint_returns_matches(self):
        response = self.client.get(reverse('product_search'), {'q': 'para', 'prefix': 'form-0'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Paracetamol 500mg')

    def test_purchase_order_create_with_searchable_line_items(self):
        branch = Product.objects.first().inventories.first().branch
        supplier = Supplier.objects.first()
        product = Product.objects.get(sku='OP-001')

        response = self.client.post(
            reverse('purchase_order_create'),
            data={
                'branch': branch.pk,
                'supplier': supplier.pk,
                'status': PurchaseOrder.Status.SENT,
                'notes': 'Demo order',
                'form-TOTAL_FORMS': '5',
                'form-INITIAL_FORMS': '0',
                'form-MIN_NUM_FORMS': '0',
                'form-MAX_NUM_FORMS': '1000',
                'form-0-product_query': product.name,
                'form-0-product_id': product.pk,
                'form-0-quantity_ordered': '4',
                'form-0-unit_price': str(product.unit_price),
            },
        )

        self.assertEqual(response.status_code, 302)
        po = PurchaseOrder.objects.latest('id')
        self.assertEqual(po.branch_id, branch.pk)
        self.assertEqual(po.supplier_id, supplier.pk)
        self.assertEqual(po.items.count(), 1)
        self.assertEqual(po.items.first().product_id, product.pk)

    def test_purchase_order_create_skips_deleted_rows(self):
        branch = Product.objects.first().inventories.first().branch
        supplier = Supplier.objects.first()
        product = Product.objects.get(sku='OP-001')
        cancelled_product = Product.objects.get(sku='OP-002')

        response = self.client.post(
            reverse('purchase_order_create'),
            data={
                'branch': branch.pk,
                'supplier': supplier.pk,
                'status': PurchaseOrder.Status.SENT,
                'notes': 'Demo order',
                'form-TOTAL_FORMS': '2',
                'form-INITIAL_FORMS': '0',
                'form-MIN_NUM_FORMS': '0',
                'form-MAX_NUM_FORMS': '1000',
                'form-0-product_query': product.name,
                'form-0-product_id': product.pk,
                'form-0-quantity_ordered': '4',
                'form-0-unit_price': str(product.unit_price),
                'form-0-DELETE': '',
                'form-1-product_query': cancelled_product.name,
                'form-1-product_id': cancelled_product.pk,
                'form-1-quantity_ordered': '8',
                'form-1-unit_price': str(cancelled_product.unit_price),
                'form-1-DELETE': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        po = PurchaseOrder.objects.latest('id')
        self.assertEqual(po.items.count(), 1)
        self.assertEqual(po.items.first().product_id, product.pk)
