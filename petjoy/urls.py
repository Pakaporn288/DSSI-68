from django.urls import path
from .views import homepage
from . import views


app_name = 'petjoy'

urlpatterns = [
    path('', homepage, name='homepage'),
    path('ask-ai/', views.ask_ai_view, name='ask_ai'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),           
]
