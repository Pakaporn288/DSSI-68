from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy
import json
from .ai_service import get_ai_response
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth import update_session_auth_hash
import logging
from django.contrib.auth import get_user_model
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Product, Review, Category, Profile
from django.db.models import Avg, Q
from .forms import ProductForm, UserUpdateForm, ProfileUpdateForm
from django.contrib.admin.views.decorators import staff_member_required

logger = logging.getLogger(__name__)

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


def logout_view(request):
    logout(request)
    messages.info(request, "คุณได้ออกจากระบบแล้ว")
    return redirect("petjoy:homepage")


def register_view(request):
    from .forms import RegisterForm
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            # Keep register flow user-only: save and redirect to login with registered flag
            form.save()
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
    return render(request, 'petjoy/products/product_detail.html', {
        'product': product,
        'reviews': reviews
    })


@require_POST
def add_to_cart(request):
    """Simple session-based cart: store {product_id: quantity} in session.
    Expects POST with 'product_id' and optional 'quantity'.
    """
    product_id = request.POST.get('product_id')
    try:
        quantity = int(request.POST.get('quantity') or 1)
    except (TypeError, ValueError):
        quantity = 1

    product = get_object_or_404(Product, id=product_id)

    cart = request.session.get('cart', {})
    key = str(product.id)
    cart[key] = cart.get(key, 0) + quantity
    request.session['cart'] = cart

    messages.success(request, f'เพิ่ม "{product.name}" ลงในตะกร้า')

    # Redirect back to referring page or homepage
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('petjoy:homepage')

def entrepreneur_profile_edit(request):
    # Only allow logged-in entrepreneurs
    entrepreneur = None
    if not request.user.is_authenticated or not hasattr(request.user, 'entrepreneur'):
        messages.error(request, 'คุณต้องเป็นผู้ประกอบการและล็อกอินเพื่อแก้ไขโปรไฟล์')
        return redirect('petjoy:login')

    entrepreneur = request.user.entrepreneur

    if request.method == "POST":
        # รับค่าจากฟอร์ม
        store_name = request.POST.get('store_name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')
        password = request.POST.get('password')
        profile_image = request.FILES.get('profile_image')

        # อัปเดตข้อมูล entrepreneur
        entrepreneur.store_name = store_name
        entrepreneur.phone = phone
        entrepreneur.email = email
        if profile_image:
            entrepreneur.profile_image = profile_image
        entrepreneur.save()

        # อัปเดตข้อมูล user (เช่น password)
        user = request.user
        if email:
            user.email = email
        if password:
            user.set_password(password)
            user.save()
            try:
                update_session_auth_hash(request, user)
            except Exception:
                pass
        else:
            user.save()

        messages.success(request, "บันทึกการเปลี่ยนแปลงสำเร็จ!")

    return render(request, 'petjoy/entrepreneur/entrepreneur_profile_edit.html', {'entrepreneur': entrepreneur})

@csrf_exempt
def entrepreneur_register(request):
    # Two modes:
    # - If user is authenticated: attach Entrepreneur to request.user
    # - If anonymous: allow creating user+entrepreneur in one flow
    from .models import Entrepreneur
    from django.contrib.auth.forms import UserCreationForm

    if request.user.is_authenticated:
        if hasattr(request.user, 'entrepreneur'):
            messages.info(request, 'คุณมีโปรไฟล์ผู้ประกอบการแล้ว')
            return redirect('petjoy:entrepreneur-home')

        if request.method == 'POST':
            store_name = request.POST.get('store_name')
            owner_name = request.POST.get('owner_name')
            email = request.POST.get('email') or request.user.email
            phone = request.POST.get('phone')

            if not store_name or not owner_name or not email:
                messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
                return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')

            # Prevent duplicate shop by email
            if Entrepreneur.objects.filter(email__iexact=email).exists():
                messages.error(request, 'มีร้านค้าที่ใช้อีเมลนี้อยู่แล้ว')
                return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')

            Entrepreneur.objects.create(
                user=request.user,
                store_name=store_name,
                owner_name=owner_name,
                email=email,
                phone=phone or ''
            )
            messages.success(request, 'สมัครเป็นผู้ประกอบการเรียบร้อยแล้ว')
            return redirect('petjoy:entrepreneur-home')

        return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')

    # Anonymous flow: create User and Entrepreneur in one form
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email')
        store_name = request.POST.get('store_name')
        owner_name = request.POST.get('owner_name')
        phone = request.POST.get('phone')

        # Basic validation
        if not username or not password or not email or not store_name or not owner_name:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
            return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')

        # Check duplicate entrepreneur email
        if Entrepreneur.objects.filter(email__iexact=email).exists():
            messages.error(request, 'มีร้านค้าที่ใช้อีเมลนี้อยู่แล้ว')
            return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')

        # Create user
        User = get_user_model()
        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, 'มีชื่อผู้ใช้นี้ในระบบแล้ว')
            return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')

        new_user = User.objects.create_user(username=username, email=email, password=password)
        # Create entrepreneur tied to new_user
        Entrepreneur.objects.create(
            user=new_user,
            store_name=store_name,
            owner_name=owner_name,
            email=email,
            phone=phone or ''
        )
        messages.success(request, 'สมัครเป็นผู้ประกอบการเรียบร้อยแล้ว กรุณาเข้าสู่ระบบ')
        return redirect('petjoy:login')

    return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')


class ProductListView(ListView):
    model = Product
    template_name = 'petjoy/products/product_list.html'
    context_object_name = 'products'

    def get_queryset(self):
        qs = super().get_queryset()
        # If the request asks for owner's products (mine=1) and user is an entrepreneur, filter
        req = getattr(self, 'request', None)
        # If user is an entrepreneur, show only their products by default. Provide ?all=1 to see all.
        if req and req.user.is_authenticated and hasattr(req.user, 'entrepreneur'):
            if req.GET.get('all') == '1':
                return qs
            return qs.filter(owner=req.user.entrepreneur)
        # For non-entrepreneurs show all products
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = getattr(self.request, 'user', None)
        ctx['is_entrepreneur'] = bool(user and getattr(user, 'entrepreneur', None))
        return ctx

class ProductDetailView(DetailView):
    model = Product
    template_name = 'petjoy/products/product_detail.html'
    context_object_name = 'product'

class ProductCreateView(CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'petjoy/products/product_form.html'
    success_url = reverse_lazy('petjoy:product-list')
    
    def dispatch(self, request, *args, **kwargs):
        # Only entrepreneurs can create products
        if not request.user.is_authenticated or not hasattr(request.user, 'entrepreneur'):
            messages.error(request, 'คุณต้องเป็นผู้ประกอบการและล็อกอินก่อนสร้างสินค้า')
            return redirect('petjoy:entrepreneur-register')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        obj = form.save(commit=False)
        # assign owner to the entrepreneur profile
        obj.owner = self.request.user.entrepreneur
        obj.save()
        return super().form_valid(form)

class ProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'petjoy/products/product_update_form.html'
    success_url = reverse_lazy('petjoy:product-list')

    def dispatch(self, request, *args, **kwargs):
        # Ensure only the owning entrepreneur can update
        if not request.user.is_authenticated or not hasattr(request.user, 'entrepreneur'):
            messages.error(request, 'คุณต้องเป็นผู้ประกอบการและล็อกอินก่อนแก้ไขสินค้า')
            return redirect('petjoy:login')
        obj = self.get_object()
        if obj.owner is None or obj.owner.user_id != request.user.id:
            messages.error(request, 'คุณไม่มีสิทธิ์แก้ไขสินค้านี้')
            return redirect('petjoy:product-list')
        return super().dispatch(request, *args, **kwargs)

class ProductDeleteView(DeleteView):
    model = Product
    template_name = 'petjoy/products/product_confirm_delete.html'
    success_url = reverse_lazy('petjoy:product-list')

    def dispatch(self, request, *args, **kwargs):
        # Only owner entrepreneur may delete
        if not request.user.is_authenticated or not hasattr(request.user, 'entrepreneur'):
            messages.error(request, 'คุณต้องเป็นผู้ประกอบการและล็อกอินก่อนลบสินค้า')
            return redirect('petjoy:login')
        obj = self.get_object()
        if obj.owner is None or obj.owner.user_id != request.user.id:
            messages.error(request, 'คุณไม่มีสิทธิ์ลบสินค้านี้')
            return redirect('petjoy:product-list')
        return super().dispatch(request, *args, **kwargs)




@login_required(login_url=reverse_lazy('petjoy:login'))
def entrepreneur_home(request):
    from .models import Product, Review, Entrepreneur
    # Ensure this user has an Entrepreneur profile
    try:
        entrepreneur = request.user.entrepreneur
    except Exception:
        messages.info(request, 'กรุณาสมัครเป็นผู้ประกอบการก่อนเข้าหน้านี้')
        return redirect('petjoy:entrepreneur-register')

    # Only show products that belong to this entrepreneur
    products = Product.objects.filter(owner=entrepreneur)
    product_count = products.count()
    all_reviews = Review.objects.filter(product__in=products)
    if all_reviews.exists():
        avg_score = round(all_reviews.aggregate(Avg('rating'))['rating__avg'], 2)
    else:
        avg_score = None
    return render(request, 'petjoy/entrepreneur/entrepreneur_home.html', {
        'product_count': product_count,
        'products': products,
        'avg_score': avg_score,
        'entrepreneur': entrepreneur,
    })

@csrf_exempt
def login_view(request):
    next_url = request.GET.get('next') or request.POST.get('next')

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            logger.debug(f"Login attempt for username (raw): '{username}'")
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                logger.debug(f"authenticate() returned user id={user.id} username={user.username}")
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
                # As a fallback, try to locate a user with a case-insensitive username
                # (helps with users who typed different case or unicode normalization differences)
                User = get_user_model()
                try:
                    found = User.objects.filter(username__iexact=username).first()
                except Exception:
                    found = None

                if found:
                    logger.debug(f"Found user by iexact lookup: {found.username} (id={found.id}) - trying authenticate with found.username")
                    user = authenticate(username=found.username, password=password)
                    if user is not None:
                        logger.debug(f"Fallback authenticate succeeded for user id={user.id}")
                        login(request, user)
                        messages.info(request, f"ยินดีต้อนรับ, {found.username}!")
                        if next_url:
                            return redirect(next_url)
                        if hasattr(user, 'entrepreneur') or hasattr(user, 'entrepreneur_profile'):
                            return redirect("petjoy:entrepreneur-home")
                        return redirect("petjoy:homepage")

                logger.debug("authenticate() failed and fallback did not find valid credentials")
                messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        else:
            # Keep the bound form so template can render specific form errors
            messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    else:
        form = AuthenticationForm(request)

    return render(request, "petjoy/login.html", context={"login_form": form, "auth_page": True, 'next': next_url})


def entrepreneur_public(request, pk):
    from .models import Entrepreneur, Product, Review
    entrepreneur = get_object_or_404(Entrepreneur, pk=pk)
    products = Product.objects.filter(owner=entrepreneur)
    product_count = products.count()
    all_reviews = Review.objects.filter(product__in=products)
    if all_reviews.exists():
        avg_score = round(all_reviews.aggregate(Avg('rating'))['rating__avg'], 2)
    else:
        avg_score = None
    return render(request, 'petjoy/entrepreneur/entrepreneur_public.html', {
        'entrepreneur': entrepreneur,
        'products': products,
        'product_count': product_count,
        'avg_score': avg_score,
    })


@login_required
def profile_view(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    # If editing (via ?edit=1) show forms and accept POST
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            password = user_form.cleaned_data.get('password')
            if password:
                user.set_password(password)
            user.save()
            profile_form.save()
            messages.success(request, 'อัปเดตข้อมูลสำเร็จ')
            # If password changed we need to re-authenticate; redirect to login
            if password:
                # Update the session auth hash so the user stays logged in after password change
                try:
                    update_session_auth_hash(request, user)
                    logger.debug(f"update_session_auth_hash called for user {user.username} (id={user.id})")
                    messages.info(request, 'เข้าสู่ระบบใหม่เรียบร้อยหลังการเปลี่ยนรหัสผ่าน')
                except Exception as e:
                    logger.exception('update_session_auth_hash failed')
                    # If update fails for any reason, fallback to asking user to log in again
                    return redirect('petjoy:login')
            return redirect('petjoy:profile')
        else:
            messages.error(request, 'มีข้อผิดพลาดในการกรอกข้อมูล')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=profile)

    return render(request, 'petjoy/profile.html', {
        'profile': profile,
        'user_form': user_form,
        'profile_form': profile_form,
        'editing': request.GET.get('edit') == '1'
    })

# สำหรับหน้าสินค้าแมว (ลูกค้าทั่วไป)
def cat_products_view(request):
    cat_category = Category.objects.filter(name__iexact='cat').first()
    products = Product.objects.filter(category=cat_category) if cat_category else Product.objects.none()
    return render(request, 'petjoy/cat_products.html', {'products': products})
# สำหรับหน้าสินค้าสุนัข (ลูกค้าทั่วไป)
def dog_products_view(request):
    dog_category = Category.objects.filter(name__iexact='dog').first()
    products = Product.objects.filter(category=dog_category) if dog_category else Product.objects.none()
    return render(request, 'petjoy/dog_products.html', {'products': products})


def food_products_view(request):
    typ_raw = request.GET.get('type', '').strip()
    typ = typ_raw.lower()
    products = Product.objects.none()

    
    map_th = {'สุนัข': 'dog', 'หมา': 'dog', 'สุนัข': 'dog', 'แมว': 'cat'}
    if typ in map_th:
        typ = map_th[typ]

    # Primary: if a subtype is requested, prefer filtering by Product.food_type
    if typ in ('dog', 'cat'):
        products = Product.objects.filter(food_type=typ)

        # If none found, try category names like 'food-dog' or fallback to 'food' category
        if not products.exists():
            cat = Category.objects.filter(Q(name__iexact=f'food-{typ}') | Q(display_name__icontains=typ)).first()
            if cat:
                products = Product.objects.filter(category=cat)
            else:
                food_cat = Category.objects.filter(Q(name__iexact='food') | Q(display_name__icontains='อาหาร')).first()
                if food_cat:
                    products = Product.objects.filter(category=food_cat).filter(
                        Q(name__icontains=typ) | Q(features__icontains=typ) | Q(description__icontains=typ)
                    )
    else:
        # No subtype: return products in 'food' category (try english name or thai display)
        food_cat = Category.objects.filter(Q(name__iexact='food') | Q(display_name__icontains='อาหาร')).first()
        if food_cat:
            products = Product.objects.filter(category=food_cat)

    # If partial requested (AJAX), return only the grid fragment
    if request.GET.get('partial') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.template.loader import render_to_string
        html = render_to_string('petjoy/partials/food_products_grid.html', {'products': products})
        from django.http import HttpResponse
        return HttpResponse(html)

    return render(request, 'petjoy/food_products.html', {'products': products, 'selected_type': typ_raw})



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


@login_required
def toggle_favorite(request):
    """AJAX endpoint to toggle favorite for the logged-in user.
    Expects POST with JSON: {"product_id": <id>} or form-encoded product_id.
    Returns JSON {"status": "added"|"removed", "favorites_count": <int>}.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    # Try to parse JSON body first, fall back to POST data
    try:
        data = json.loads(request.body.decode('utf-8')) if request.body else {}
    except Exception:
        data = {}

    product_id = data.get('product_id') or request.POST.get('product_id')
    if not product_id:
        return JsonResponse({'error': 'product_id required'}, status=400)

    product = get_object_or_404(Product, id=product_id)
    profile, _ = Profile.objects.get_or_create(user=request.user)

    if product in profile.favorites.all():
        profile.favorites.remove(product)
        status = 'removed'
    else:
        profile.favorites.add(product)
        status = 'added'

    return JsonResponse({'status': status, 'favorites_count': profile.favorites.count()})


@login_required
def favorites_list(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    products = profile.favorites.all()
    return render(request, 'petjoy/favorites_list.html', {'products': products})