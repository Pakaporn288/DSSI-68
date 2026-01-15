# petjoy/urls.py
from django.urls import path
from . import views
from .views import EntrepreneurProductDetailView, entrepreneur_register
from .views import entrepreneur_home
from .views import entrepreneur_chat_list, entrepreneur_chat_room, entrepreneur_chat_delete


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
    path('entrepreneur/profile/edit/', views.entrepreneur_profile_edit_home, name='entrepreneur-profile-edit-home'),
    path('ask-ai/', views.ask_ai_view, name='ask-ai'),
    path('search/', views.search_view, name='search'),
    path('cart/add/', views.add_to_cart, name='cart-add'),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="cart-remove"),
    path('favorites/', views.favorites_list, name='favorites-list'),
    path('cart/', views.cart_detail, name='cart-detail'),     
    path('cart/add/', views.add_to_cart, name='cart-add'), 
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove-from-cart'),
    path('cart/update/', views.update_cart, name='update-cart'),
    path('checkout/', views.checkout_view, name='checkout'),
    # alias with underscore because some templates use 'favorites_list'
    path('favorites/', views.favorites_list, name='favorites_list'),
    path('favorites/toggle/', views.toggle_favorite, name='favorites-toggle'),
    path('dog-products/', views.dog_products_view, name='dog-products'),
    path('cat-products/', views.cat_products_view, name='cat-products'),
    path('food-products/', views.food_products_view, name='food-products'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/address/', views.address_list, name='address_list'),
    path('profile/address/add/', views.address_add, name='address_add'),
    path('profile/address/edit/<int:id>/', views.address_edit, name='address_edit'),
    path('profile/address/delete/<int:id>/', views.address_delete, name='address_delete'),
    path('profile/address/set-default/<int:id>/', views.address_set_default, name='address_set_default'),
    path("profile/address/", views.address_list, name="address_list"),
    path("profile/address/add/", views.address_add, name="address_add"),
    path("profile/address/edit/<int:id>/", views.address_edit, name="address_edit"),
    path("profile/address/delete/<int:id>/", views.address_delete, name="address_delete"),
    path("profile/address/set-default/<int:id>/", views.address_set_default, name="address_set_default"),
    path('products/create/', views.ProductCreateView.as_view(), name='product-create'),
    path('products/<int:pk>/update/', views.ProductUpdateView.as_view(), name='product-update'),
    path('products/<int:pk>/delete/', views.ProductDeleteView.as_view(), name='product-delete'),
    path('orders/', views.orders_list, name="orders-list"),
    path('orders/<int:order_id>/update-status/', views.update_order_status, name="update-order-status"),
    path('entrepreneur/product/<int:pk>/',EntrepreneurProductDetailView.as_view(),name="entrepreneur-product-detail"),
    path("order-history/", views.order_history, name="order_history"),
    path("order/detail/<int:order_id>/", views.order_detail_customer, name="order-detail-customer"),
    path('orders/history/', views.order_history, name="order_history"),
    path('orders/history/<int:order_id>/', views.order_detail_customer, name="order_detail_customer"),
    path('orders/', views.orders_list, name="orders-list"), 
    path('chat/', views.chat_list, name='chat_list'),
    path('chat/start/<int:entrepreneur_id>/', views.start_chat_view, name='start_chat'),
    path('chat/room/<int:room_id>/', views.chat_room, name='chat_room'),
    path('chat/delete/<int:room_id>/', views.delete_chat, name='delete_chat'),
    path('entrepreneur/chat/', entrepreneur_chat_list, name='entrepreneur-chat-list'),
    path('entrepreneur/chat/room/<int:room_id>/', entrepreneur_chat_room, name='entrepreneur-chat-room'),
    path('entrepreneur/chat/delete/<int:room_id>/', entrepreneur_chat_delete, name='entrepreneur-chat-delete'),
    path("entrepreneur/profile/settings/", views.entrepreneur_profile_settings, name="entrepreneur_profile_settings"),
    path("orders/<int:order_id>/", views.order_detail, name="orders-detail"),
    path("notifications/", views.notification_list, name="notification_list"),
    path("review/<int:order_id>/", views.review_product, name="review_product"),
    path('product/<int:product_id>/report/', views.report_product, name='report_product'),
    path('entrepreneur/reviews/',views.entrepreneur_reviews, name='entrepreneur_reviews' ),
    path('entrepreneur/review/<int:review_id>/reply/',views.reply_review,name='reply_review'),
    path("review/<int:order_id>/", views.review_product, name="review_product"),
    path("entrepreneur/income/", views.entrepreneur_income, name="entrepreneur-income"),
    path("system/dashboard/", views.admin_dashboard, name="admin-dashboard"),
    path("system/users/", views.admin_user_list, name="admin-users"),
    path("system/users/<int:user_id>/",views.admin_user_detail,name="admin-user-detail"),







]





