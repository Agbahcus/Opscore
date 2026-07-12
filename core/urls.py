from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('branches/', views.branches_list, name='branches_list'),
    path('branches/<int:pk>/', views.branch_detail, name='branch_detail'),
    path('products/', views.products_list, name='products_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('products/search/', views.product_search, name='product_search'),
    path('inventory/', views.inventory_view, name='inventory_view'),
    path('purchase-orders/', views.purchase_orders_list, name='purchase_orders_list'),
    path('purchase-orders/create/', views.purchase_order_create, name='purchase_order_create'),
    path('purchase-orders/<int:pk>/', views.purchase_order_detail, name='purchase_order_detail'),
    path('suppliers/', views.suppliers_list, name='suppliers_list'),
    path('suppliers/<int:pk>/', views.supplier_detail, name='supplier_detail'),
    path('adjustments/create/', views.adjustment_create, name='adjustment_create'),
    path('reports/', views.reports_index, name='reports_index'),
    path('reports/<int:branch_id>/<str:report_date>/', views.reports_detail, name='report_detail'),
]
