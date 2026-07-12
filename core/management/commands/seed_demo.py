import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import F
from django.db import transaction
from django.utils import timezone

from core.models import (
    Branch,
    BranchInventory,
    Category,
    DailyReport,
    Product,
    PurchaseOrder,
    PurchaseOrderItem,
    StockMovement,
    Supplier,
    SupplierPayment,
)


class Command(BaseCommand):
    help = 'Seed demo data for the OpsCore proof project.'

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(42)
        now = timezone.now()

        BranchInventory.objects.all().delete()
        PurchaseOrderItem.objects.all().delete()
        PurchaseOrder.objects.all().delete()
        SupplierPayment.objects.all().delete()
        StockMovement.objects.all().delete()
        DailyReport.objects.all().delete()
        Product.objects.all().delete()
        Category.objects.all().delete()
        Supplier.objects.all().delete()
        Branch.objects.all().delete()

        branches = [
            Branch.objects.create(name='Ikeja branch', location='Ikeja, Lagos', manager_name='Tunde Akinwale'),
            Branch.objects.create(name='Victoria Island branch', location='Victoria Island, Lagos', manager_name='Aisha Bello'),
            Branch.objects.create(name='Lekki branch', location='Lekki, Lagos', manager_name='Ngozi Okafor'),
        ]

        suppliers = [
            Supplier.objects.create(
                name='Emzor Pharmaceuticals',
                contact_name='Bola Martins',
                phone='08031234567',
                email='orders@emzor.example',
                products_supplied='Analgesics, antibiotics, vitamins',
            ),
            Supplier.objects.create(
                name='Multipro Consumer Products',
                contact_name='Kunle Adeyemi',
                phone='08039876543',
                email='sales@multipro.example',
                products_supplied='Household, personal care, FMCG',
            ),
        ]

        categories = {name: Category.objects.create(name=name) for name in [
            'Analgesics', 'Antibiotics', 'Vitamins', 'Personal Care', 'Household'
        ]}

        products = [
            ('Paracetamol 500mg', 'OP-001', 'Analgesics', 'tablets', '1500.00', 12),
            ('Ibuprofen 200mg', 'OP-002', 'Analgesics', 'tablets', '2200.00', 10),
            ('Amoxicillin 500mg', 'OP-003', 'Antibiotics', 'tablets', '4800.00', 8),
            ('Augmentin 625mg', 'OP-004', 'Antibiotics', 'tablets', '9200.00', 5),
            ('Vitamin C 1000mg', 'OP-005', 'Vitamins', 'tablets', '3600.00', 10),
            ('B-Complex', 'OP-006', 'Vitamins', 'tablets', '4100.00', 10),
            ('Dettol Liquid 500ml', 'OP-007', 'Personal Care', 'bottles', '7800.00', 6),
            ('Milo Sachet', 'OP-008', 'Household', 'sachets', '350.00', 30),
            ('Peak Milk 400g', 'OP-009', 'Household', 'packs', '6800.00', 8),
            ('Detergent Powder 1kg', 'OP-010', 'Household', 'packs', '5400.00', 12),
            ('Castor Oil 250ml', 'OP-011', 'Personal Care', 'bottles', '2600.00', 7),
            ('Zinc Sulfate Syrup', 'OP-012', 'Vitamins', 'bottles', '3300.00', 9),
            ('Cough Syrup 100ml', 'OP-013', 'Analgesics', 'bottles', '2900.00', 7),
            ('Antacid Suspension', 'OP-014', 'Analgesics', 'bottles', '2700.00', 7),
            ('Hand Sanitizer 500ml', 'OP-015', 'Personal Care', 'bottles', '2400.00', 10),
            ('Toothpaste 100g', 'OP-016', 'Personal Care', 'packs', '1800.00', 15),
            ('Soap Bar Carton', 'OP-017', 'Household', 'cartons', '11000.00', 4),
            ('ORS Sachets', 'OP-018', 'Vitamins', 'sachets', '1200.00', 20),
            ('Multivitamin Syrup', 'OP-019', 'Vitamins', 'bottles', '5100.00', 8),
            ('Pain Relief Gel', 'OP-020', 'Analgesics', 'packs', '4300.00', 6),
        ]

        product_objs = []
        for name, sku, category_name, unit, price, reorder_point in products:
            product_objs.append(
                Product.objects.create(
                    name=name,
                    sku=sku,
                    category=categories[category_name],
                    unit=unit,
                    unit_price=Decimal(price),
                    reorder_point=reorder_point,
                )
            )

        for branch in branches:
            for product in product_objs:
                quantity = random.choice([0, random.randint(1, product.reorder_point), random.randint(product.reorder_point + 1, product.reorder_point + 25)])
                inventory = BranchInventory.objects.create(branch=branch, product=product, quantity=quantity)
                if quantity:
                    remaining = quantity
                    parts = random.randint(1, min(3, quantity))
                    splits = []
                    for index in range(parts - 1):
                        max_allowed = remaining - (parts - index - 1)
                        split = random.randint(1, max_allowed)
                        splits.append(split)
                        remaining -= split
                    splits.append(remaining)
                    receipt_days = sorted(random.sample(range(1, 6), k=parts))
                    for qty, days_back in zip(splits, receipt_days):
                        movement = StockMovement.objects.create(
                            branch=branch,
                            product=product,
                            movement_type=StockMovement.MovementType.RECEIPT,
                            quantity_change=qty,
                            reference='SEED',
                            notes='Historical seeded stock',
                            created_by='Seeder',
                        )
                        StockMovement.objects.filter(pk=movement.pk).update(created_at=now - timedelta(days=days_back))

        po1 = PurchaseOrder.objects.create(branch=branches[0], supplier=suppliers[0], status=PurchaseOrder.Status.DRAFT, notes='Seed draft PO')
        PurchaseOrderItem.objects.create(purchase_order=po1, product=product_objs[0], quantity_ordered=20, unit_price=product_objs[0].unit_price)

        po2 = PurchaseOrder.objects.create(branch=branches[1], supplier=suppliers[0], status=PurchaseOrder.Status.PARTIALLY_RECEIVED, notes='Seed partial PO')
        PurchaseOrderItem.objects.create(purchase_order=po2, product=product_objs[0], quantity_ordered=40, quantity_received=15, unit_price=product_objs[0].unit_price)
        BranchInventory.objects.filter(branch=branches[1], product=product_objs[0]).update(quantity=F('quantity') + 15)
        po2_movement = StockMovement.objects.create(
            branch=branches[1],
            product=product_objs[0],
            movement_type=StockMovement.MovementType.RECEIPT,
            quantity_change=15,
            reference=po2.po_number,
            notes='Partial PO receipt',
            created_by='Seeder',
        )
        StockMovement.objects.filter(pk=po2_movement.pk).update(created_at=now)

        po3 = PurchaseOrder.objects.create(branch=branches[2], supplier=suppliers[1], status=PurchaseOrder.Status.FULLY_RECEIVED, notes='Seed received PO')
        PurchaseOrderItem.objects.create(purchase_order=po3, product=product_objs[6], quantity_ordered=12, quantity_received=12, unit_price=product_objs[6].unit_price)
        BranchInventory.objects.filter(branch=branches[2], product=product_objs[6]).update(quantity=F('quantity') + 12)
        po3_movement = StockMovement.objects.create(
            branch=branches[2],
            product=product_objs[6],
            movement_type=StockMovement.MovementType.RECEIPT,
            quantity_change=12,
            reference=po3.po_number,
            notes='Full PO receipt',
            created_by='Seeder',
        )
        StockMovement.objects.filter(pk=po3_movement.pk).update(created_at=now)

        SupplierPayment.objects.create(
            supplier=suppliers[0],
            purchase_order=po2,
            amount=Decimal('15000.00'),
            payment_date=timezone.localdate(),
            reference='PAY-EMZOR-001',
            notes='Partial payment',
        )
        SupplierPayment.objects.create(
            supplier=suppliers[1],
            purchase_order=po3,
            amount=Decimal('90000.00'),
            payment_date=timezone.localdate(),
            reference='PAY-MULTIPRO-001',
            notes='Full payment',
        )

        yesterday = timezone.localdate() - timedelta(days=1)
        for branch in branches:
            DailyReport.generate_for(branch, yesterday)

        self.stdout.write(self.style.SUCCESS('Demo data seeded successfully.'))
