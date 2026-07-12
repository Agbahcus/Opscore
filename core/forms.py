from django import forms
from django.forms import formset_factory
from django.db.models import Q

from .models import Branch, Product, PurchaseOrder, Supplier


class PurchaseOrderMetaForm(forms.Form):
    branch = forms.ModelChoiceField(queryset=Branch.objects.all())
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all())
    status = forms.ChoiceField(choices=PurchaseOrder.Status.choices, initial=PurchaseOrder.Status.SENT)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))


class PurchaseOrderLineForm(forms.Form):
    product_query = forms.CharField(required=False, label='Product')
    product_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    quantity_ordered = forms.IntegerField(min_value=1)
    unit_price = forms.DecimalField(min_value=0, decimal_places=2, max_digits=12)

    def clean(self):
        cleaned = super().clean()
        product = None
        product_id = cleaned.get('product_id')
        product_query = (cleaned.get('product_query') or '').strip()
        if not product_id and not product_query and not cleaned.get('quantity_ordered') and not cleaned.get('unit_price'):
            return cleaned
        if product_id:
            product = Product.objects.filter(pk=product_id).first()
        elif product_query:
            product = (
                Product.objects.filter(Q(name__icontains=product_query) | Q(sku__icontains=product_query))
                .order_by('name')
                .first()
            )
        if product is None:
            raise forms.ValidationError('Select a product from the suggestions.')
        cleaned['product'] = product
        return cleaned


PurchaseOrderLineFormSet = formset_factory(PurchaseOrderLineForm, extra=1, can_delete=True)


class SupplierPaymentForm(forms.Form):
    supplier = forms.ModelChoiceField(queryset=Supplier.objects.all())
    amount = forms.DecimalField(min_value=0, decimal_places=2, max_digits=12)
    payment_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    reference = forms.CharField()
    purchase_order = forms.ModelChoiceField(queryset=PurchaseOrder.objects.all(), required=False)
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))


class StockAdjustmentForm(forms.Form):
    branch = forms.ModelChoiceField(queryset=Branch.objects.all())
    product = forms.ModelChoiceField(queryset=Product.objects.all())
    quantity_change = forms.IntegerField()
    reason = forms.ChoiceField(choices=[
        ('damage', 'Damage'),
        ('count_correction', 'Count correction'),
        ('theft', 'Theft'),
    ])
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={'rows': 3}))
    created_by = forms.CharField(initial='Admin')
