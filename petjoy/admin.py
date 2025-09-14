from django.contrib import admin
from .models import Product
from .models import Product, Category, Review, Profile
# Register your models here.
admin.site.register(Product)
admin.site.register(Category)
admin.site.register(Review)
admin.site.register(Profile) 
