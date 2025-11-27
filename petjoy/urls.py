# petjoy/urls.py
from django.urls import path
from . import views
from .views import entrepreneur_register
from .views import entrepreneur_home

app_name = 'petjoy'

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('products/', views.ProductListView.as_view(), name='product-list'),
    path('product/<int:product_id>/', views.product_detail_view, name='product-detail'),
    path('register/', views.register_view, name='register'),
    path('entrepreneur/register/', entrepreneur_register, name='entrepreneur-register'),
    path('entrepreneur_home/', entrepreneur_home, name='entrepreneur-home'),
    path('entrepreneur/<int:pk>/', views.entrepreneur_public, name='entrepreneur-public'),
    path('entrepreneur/profile/edit/', views.entrepreneur_profile_edit, name='entrepreneur-profile-edit'),
    path('ask-ai/', views.ask_ai_view, name='ask-ai'),
    path('search/', views.search_view, name='search'),
    path('cart/add/', views.add_to_cart, name='cart-add'),
    path('favorites/', views.favorites_list, name='favorites-list'),
    path('cart/', views.cart_detail, name='cart-detail'),     
    path('cart/add/', views.add_to_cart, name='cart-add'), 
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove-from-cart'),
    path('cart/update/', views.update_cart, name='update-cart'),
    # alias with underscore because some templates use 'favorites_list'
    path('favorites/', views.favorites_list, name='favorites_list'),
    path('favorites/toggle/', views.toggle_favorite, name='favorites-toggle'),
    path('dog-products/', views.dog_products_view, name='dog-products'),
    path('cat-products/', views.cat_products_view, name='cat-products'),
    path('food-products/', views.food_products_view, name='food-products'),
    path('profile/', views.profile_view, name='profile'),
    # โค้ดสำหรับอนาคต (CRUD) สามารถเก็บไว้ได้
    path('products/create/', views.ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/update/', views.ProductUpdateView.as_view(), name='product-update'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product-delete'),
]