from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .ai_service import get_ai_response
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Product, Review, Category
from django.db.models import Avg, Q
from .forms import ProductForm
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from .models import Profile
from .models import Category

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

        # Save chat history
        from .models import ChatHistory
        ChatHistory.objects.create(
            user=request.user if request.user.is_authenticated else None,
            user_message=user_message,
            ai_response=ai_reply
        )

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
    # ✅ สำคัญ: ต้องส่ง context 'auth_page': True ด้วย
    return render(request, "petjoy/login.html", context={"login_form": form, "auth_page": True})

def logout_view(request):
    logout(request)
    messages.info(request, "คุณได้ออกจากระบบแล้ว")
    return redirect("petjoy:homepage")


def register_view(request):
    from .forms import RegisterForm
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            # Redirect to login and include a flag + username so the login page can show a message and prefill
            username = form.cleaned_data.get('username')
            messages.success(request, "สมัครสมาชิกสำเร็จ! กรุณาเข้าสู่ระบบ")
            return redirect(f"{reverse_lazy('petjoy:login')}?registered=1&username={username}")
        else:
            return render(request, "petjoy/register.html", {'form': form, 'auth_page': True})

    form = RegisterForm()
    return render(request, 'petjoy/register.html', {'form': form, 'auth_page': True})


# If you want to show reviews, use this version:
def product_detail_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.all().order_by('-created_at')
    return render(request, 'petjoy/product_detail.html', {
        'product': product,
        'reviews': reviews
    })

def entrepreneur_profile_edit(request):
    entrepreneur = None
    if hasattr(request.user, 'entrepreneur'):
        entrepreneur = request.user.entrepreneur

    if request.method == "POST" and entrepreneur:
        # รับค่าจากฟอร์ม
        store_name = request.POST.get('store_name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password = request.POST.get('password')
        profile_image = request.FILES.get('profile_image')

        # อัปเดตข้อมูล
        entrepreneur.store_name = store_name
        entrepreneur.phone = phone
        if profile_image:
            entrepreneur.profile_image = profile_image
        entrepreneur.save()

        # อัปเดตข้อมูล user
        user = request.user
        user.email = email
        if password:
            user.set_password(password)
        user.save()

        messages.success(request, "บันทึกการเปลี่ยนแปลงสำเร็จ!")
        # render หน้าเดิมพร้อมข้อมูลใหม่
    return render(request, 'petjoy/entrepreneur/entrepreneur_profile_edit.html', {'entrepreneur': entrepreneur})


class ProductListView(ListView):
    model = Product
    template_name = 'petjoy/product_list.html'
    context_object_name = 'products'

class ProductDetailView(DetailView):
    model = Product
    template_name = 'petjoy/product_detail.html'
    context_object_name = 'product'

class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'petjoy/product_form.html'
    success_url = reverse_lazy('petjoy:product-list')

class ProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'petjoy/product_update_form.html'
    success_url = reverse_lazy('petjoy:product-list')

class ProductDeleteView(DeleteView):
    model = Product
    template_name = 'petjoy/product_confirm_delete.html'
    success_url = reverse_lazy('petjoy:product-list')


def entrepreneur_register(request):
    return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')



@login_required
def entrepreneur_home(request):
    # (ลบการเช็คว่า user ต้องเป็น entrepreneur)
    from .models import Product, Review
    products = Product.objects.all()
    product_count = products.count()
    all_reviews = Review.objects.filter(product__in=products)
    if all_reviews.exists():
        avg_score = round(all_reviews.aggregate(Avg('rating'))['rating__avg'], 2)
    else:
        avg_score = None
    return render(request, 'petjoy/entrepreneur/entrepreneur_home.html', {
        'product_count': product_count,
        'products': products,
        'avg_score': avg_score
    })

def login_view(request):
    # Support redirecting to a `next` URL after login (from ?next=...)
    next_url = request.GET.get('next') or request.POST.get('next')

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"ยินดีต้อนรับ, {username}!")

                # If a next URL was provided, use it first.
                if next_url:
                    return redirect(next_url)

                # Redirect entrepreneur users to entrepreneur_home, others to homepage
                if hasattr(user, 'entrepreneur') or hasattr(user, 'entrepreneur_profile'):
                    return redirect("petjoy:entrepreneur-home")

                return redirect("petjoy:homepage")
            else:
                messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        else:
            messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    form = AuthenticationForm()
    return render(request, "petjoy/login.html", context={"login_form": form, "auth_page": True})

# หน้าโปรไฟล์ผู้ใช้ทั่วไป

@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    return render(request, 'petjoy/profile.html', {'profile': profile})
# สำหรับหน้าสินค้าแมว (ลูกค้าทั่วไป)
def cat_products_view(request):
    cat_category = Category.objects.filter(name__iexact='cat').first()
    products = Product.objects.filter(category=cat_category) if cat_category else Product.objects.none()
    return render(request, 'petjoy/cat_products.html', {'products': products})
from .models import Product, Review, Category
# สำหรับหน้าสินค้าสุนัข (ลูกค้าทั่วไป)
def dog_products_view(request):
    dog_category = Category.objects.filter(name__iexact='dog').first()
    products = Product.objects.filter(category=dog_category) if dog_category else Product.objects.none()
    return render(request, 'petjoy/dog_products.html', {'products': products})



def search_view(request):
    q = request.GET.get('q', '').strip()
    products = Product.objects.none()
    categories = Category.objects.none()
    if q:
        products = Product.objects.filter(
            Q(name__icontains=q) | Q(description__icontains=q) | Q(features__icontains=q)
        )
        categories = Category.objects.filter(name__icontains=q) | Category.objects.filter(display_name__icontains=q)

    return render(request, 'petjoy/search_results.html', {
        'query': q,
        'products': products,
        'categories': categories,
    })
