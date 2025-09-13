# petjoy/urls.py
from django.urls import path
from . import views

app_name = 'petjoy'

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('product/<int:product_id>/', views.product_detail_view, name='product-detail'),
    path('register/', views.register_view, name='register'),
    # โค้ดสำหรับอนาคต (CRUD) สามารถเก็บไว้ได้
    # path('products/create/', views.ProductCreateView.as_view(), name='product-create'),
    # path('products/<int:pk>/update/', views.ProductUpdateView.as_view(), name='product-update'),
    # path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product-delete'),
]