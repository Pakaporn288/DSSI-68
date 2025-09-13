# views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .ai_service import get_ai_response
from .forms import NewUserForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages 
from django.contrib.auth import login, authenticate, logout
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Product # <-- ตรวจสอบว่ามีการ import Product
from .forms import ProductForm
from .models import Product, Review

def homepage(request):
    products = Product.objects.all()[:4]
    return render(request, 'petjoy/homepage.html', {'products': products})

def ask_ai_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get('message')

        if not user_message:
            return JsonResponse({'error': 'No message provided'}, status=400)

        ai_reply = get_ai_response(user_message)
        return JsonResponse({'reply': ai_reply})

    return JsonResponse({'error': 'Invalid request method'}, status=405)

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"ยินดีต้อนรับกลับมา, {username}")
                return redirect("petjoy:homepage")
            else:
                messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        else:
            messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    form = AuthenticationForm()
    return render(request, "petjoy/login.html", context={"login_form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "คุณได้ออกจากระบบแล้ว")
    return redirect("petjoy:homepage")

def product_detail_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'petjoy/product_detail.html', {'product': product})

def product_detail_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    # ดึงรีวิวทั้งหมดของสินค้านี้ เรียงจากใหม่ไปเก่า
    reviews = product.reviews.all().order_by('-created_at')
    
    # ส่งข้อมูลทั้ง product และ reviews ไปที่ Template
    return render(request, 'petjoy/product_detail.html', {
        'product': product,
        'reviews': reviews
    })

class ProductListView(ListView):
    model = Product
    template_name = 'product_list.html'
    context_object_name = 'products'

class ProductDetailView(DetailView):
    model = Product
    template_name = 'product_detail.html'
    context_object_name = 'product'

class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'product_form.html'
    success_url = reverse_lazy('product-list')

class ProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'product_form.html'
    success_url = reverse_lazy('product-list')

class ProductDeleteView(DeleteView):
    model = Product
    template_name = 'product_confirm_delete.html'
    success_url = reverse_lazy('product-list')

