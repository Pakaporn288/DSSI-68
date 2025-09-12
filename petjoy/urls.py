from django.urls import path
from .views import (
    homepage,
    ProductListView,
    ProductDetailView,
    ProductCreateView,
    ProductUpdateView,
    ProductDeleteView,
    login_view,
    logout_view,
)

app_name = 'petjoy'

urlpatterns = [
    path('', homepage, name='homepage'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/create/', ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/update/', ProductUpdateView.as_view(), name='product-update'),
    path('products/<int:pk>/delete/', ProductDeleteView.as_view(), name='product-delete'),
]
