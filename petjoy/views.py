from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy
import json
from django.views import View
from .ai_service import get_ai_response
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth import update_session_auth_hash
import logging
from django.contrib.auth import get_user_model
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import Product, Review, Category, Profile, CartItem   
from django.db.models import Avg, Q
from django.core.paginator import Paginator
from .forms import ProductForm, UserUpdateForm, ProfileUpdateForm
from django.contrib.admin.views.decorators import staff_member_required
from .models import Address
from django.utils.decorators import method_decorator
from django.contrib.auth import update_session_auth_hash
from .models import Order, OrderItem

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


@login_required(login_url='petjoy:login')
@require_POST
def add_to_cart(request):
    """เพิ่มสินค้าเข้าตะกร้าของ user"""
    product_id = request.POST.get("product_id")
    quantity = int(request.POST.get("quantity") or 1)

    product = get_object_or_404(Product, id=product_id)

    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        cart_item.quantity += quantity

    cart_item.save()

    messages.success(request, f"เพิ่ม {product.name} x{quantity} ลงตะกร้าแล้ว!")

    return redirect(request.META.get("HTTP_REFERER", "petjoy:homepage"))

@login_required(login_url='petjoy:login')
def remove_from_cart(request, item_id):
    """ลบรายการสินค้าออกจากตะกร้าของ user"""
    # ใช้ item_id ซึ่งคือ CartItem.id
    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)
    
    # ลบรายการนั้น
    product_name = cart_item.product.name
    cart_item.delete()

    messages.success(request, f"ลบ {product_name} ออกจากตะกร้าแล้ว")

    # นำกลับไปยังหน้าตะกร้าสินค้า
    return redirect("petjoy:cart-detail")

@login_required(login_url='petjoy:login')
@require_POST
def update_cart(request):
    """อัปเดตจำนวนสินค้าในตะกร้า (ใช้กับปุ่ม + / -)"""
    item_id = request.POST.get("item_id")
    new_qty = int(request.POST.get("quantity") or 0)

    cart_item = get_object_or_404(CartItem, id=item_id, user=request.user)

    if new_qty <= 0:
        product_name = cart_item.product.name
        cart_item.delete()
        messages.info(request, f"ลบ {product_name} ออกจากตะกร้าแล้ว")
    else:
        cart_item.quantity = new_qty
        cart_item.save()
        messages.success(request, f"อัปเดต {cart_item.product.name} เป็น {new_qty} ชิ้นแล้ว")

    return redirect("petjoy:cart-detail")


@login_required(login_url='petjoy:login')
def cart_detail(request):
    cart_items = CartItem.objects.filter(user=request.user)

    total_price = sum(item.total_price for item in cart_items)

    # NEW: จำนวนสินค้าทั้งหมดในตะกร้า (รวมจำนวน ไม่ใช่จำนวนรายการ)
    total_items = sum(item.quantity for item in cart_items)

    return render(request, "petjoy/cart_detail.html", {
        "cart_items": cart_items,
        "total_price": total_price,
        "total_items": total_items  # NEW
    })

@login_required
def entrepreneur_profile_edit_home(request):
    if not hasattr(request.user, 'entrepreneur'):
        messages.error(request, "คุณต้องเป็นผู้ประกอบการก่อนแก้ไขโปรไฟล์")
        return redirect("petjoy:login")

    entrepreneur = request.user.entrepreneur

    if request.method == "POST":
        store_name = request.POST.get("store_name")
        owner_name = request.POST.get("owner_name")
        phone = request.POST.get("phone")
        email = request.POST.get("email")
        password = request.POST.get("password")
        profile_image = request.FILES.get("profile_image")

        entrepreneur.store_name = store_name
        entrepreneur.owner_name = owner_name
        entrepreneur.phone = phone
        entrepreneur.email = email

        if profile_image:
            entrepreneur.profile_image = profile_image

        entrepreneur.save()

        # อัปเดต User
        user = request.user
        user.email = email
        if password:
            user.set_password(password)
        user.save()

        update_session_auth_hash(request, user)

        messages.success(request, "บันทึกโปรไฟล์เรียบร้อยแล้ว!")

    return render(
        request,
        "petjoy/entrepreneur/entrepreneur_profile_edit_home.html",
        {"entrepreneur": entrepreneur}
    )

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
        password2 = request.POST.get('password2')
        email = request.POST.get('email')
        store_name = request.POST.get('store_name')
        owner_name = request.POST.get('owner_name')
        phone = request.POST.get('phone')

        # Basic validation
        if not username or not password or not email or not store_name or not owner_name:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
            return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')

        # confirm password
        if password2 is None or password != password2:
            messages.error(request, 'รหัสผ่านทั้งสองช่องต้องตรงกัน')
            return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')

        # strip whitespace from username/email to avoid accidental spaces
        username = username.strip()
        if email:
            email = email.strip()

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

        # Log the user in immediately so they can manage their shop
        try:
            login(request, new_user)
            messages.success(request, 'สมัครและเข้าสู่ระบบเรียบร้อยแล้ว')
            return redirect('petjoy:entrepreneur-home')
        except Exception:
            # If automatic login fails for any reason, ask user to login manually
            messages.success(request, 'สมัครเป็นผู้ประกอบการเรียบร้อยแล้ว กรุณาเข้าสู่ระบบ')
            return redirect('petjoy:login')

    return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')

def address_list(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'petjoy/address_list.html', {'addresses': addresses})


def address_add(request):
    if request.method == "POST":
        Address.objects.create(
            user=request.user,
            full_name=request.POST['full_name'],
            phone=request.POST['phone'],
            address_line=request.POST['address_line'],
            subdistrict=request.POST['subdistrict'],
            district=request.POST['district'],
            province=request.POST['province'],
            zipcode=request.POST['zipcode'],
        )
        return redirect('petjoy:address_list')

    return render(request, 'petjoy/address_form.html')


def address_edit(request, id):
    address = Address.objects.get(id=id, user=request.user)

    if request.method == "POST":
        address.full_name = request.POST['full_name']
        address.phone = request.POST['phone']
        address.address_line = request.POST['address_line']
        address.subdistrict = request.POST['subdistrict']
        address.district = request.POST['district']
        address.province = request.POST['province']
        address.zipcode = request.POST['zipcode']
        address.save()
        return redirect('petjoy:address_list')

    return render(request, 'petjoy/address_form.html', {"address": address})


def address_delete(request, id):
    Address.objects.get(id=id, user=request.user).delete()
    return redirect('petjoy:address_list')


def address_set_default(request, id):
    Address.objects.filter(user=request.user).update(is_default=False)
    Address.objects.filter(id=id, user=request.user).update(is_default=True)
    return redirect('petjoy:address_list')

def address_edit(request, id):
    address = Address.objects.get(id=id, user=request.user)

    if request.method == "POST":
        address.full_name = request.POST["full_name"]
        address.phone = request.POST["phone"]
        address.address_line = request.POST["address_line"]
        address.subdistrict = request.POST["subdistrict"]
        address.district = request.POST["district"]
        address.province = request.POST["province"]
        address.zipcode = request.POST["zipcode"]
        address.save()
        return redirect("petjoy:address_list")

    return render(request, "petjoy/address_form.html", {"address": address})

class EntrepreneurProductDetailView(View):
    def get(self, request, pk):
        if not request.user.is_authenticated or not hasattr(request.user, 'entrepreneur'):
            return redirect('petjoy:login')

        product = get_object_or_404(Product, pk=pk, owner=request.user.entrepreneur)

        return render(request, "petjoy/entrepreneur/entrepreneur_product_detail.html", {
            "product": product,
            "entrepreneur": request.user.entrepreneur
        })

class ProductListView(ListView):
    model = Product
    template_name = 'petjoy/products/product_list.html'
    context_object_name = 'products'

    def get_queryset(self):
        qs = super().get_queryset()
        req = self.request

        # ถ้าเป็นผู้ประกอบการ → ให้เห็นเฉพาะสินค้าของตัวเอง (ยกเว้น ?all=1)
        if req.user.is_authenticated and hasattr(req.user, 'entrepreneur'):
            ent = req.user.entrepreneur
            if req.GET.get('all') != '1':
                qs = qs.filter(owner=ent)

        # ----- กรองตามชื่อสินค้า (optional) -----
        search_query = req.GET.get('search', '').strip()
        if search_query:
            qs = qs.filter(name__icontains=search_query)

        # ----- กรองตามหมวดหมู่ -----
        category_id = req.GET.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        # ส่ง entrepreneur เข้า template ให้ sidebar ใช้
        if user.is_authenticated and hasattr(user, 'entrepreneur'):
            ctx['entrepreneur'] = user.entrepreneur
            ctx['is_entrepreneur'] = True
        else:
            ctx['entrepreneur'] = None
            ctx['is_entrepreneur'] = False

        # ส่ง categories ให้ dropdown ใช้
        ctx['categories'] = Category.objects.all()
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
        if not request.user.is_authenticated or not hasattr(request.user, 'entrepreneur'):
            messages.error(request, 'คุณต้องเป็นผู้ประกอบการและล็อกอินก่อนเพิ่มสินค้า')
            return redirect('petjoy:login')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['entrepreneur'] = self.request.user.entrepreneur
        return ctx

    def form_valid(self, form):
        form.instance.owner = self.request.user.entrepreneur
        messages.success(self.request, "เพิ่มสินค้าเรียบร้อยแล้ว!")
        return super().form_valid(form)

@method_decorator(login_required, name='dispatch')
class ProductUpdateView(UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'petjoy/products/product_update_form.html'
    context_object_name = 'product'
    success_url = reverse_lazy('petjoy:product-list')

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(request.user, 'entrepreneur'):
            messages.error(request, "คุณต้องเป็นผู้ประกอบการเพื่อแก้ไขสินค้า")
            return redirect('petjoy:login')

        product = self.get_object()
        if product.owner != request.user.entrepreneur:
            messages.error(request, "คุณไม่มีสิทธิ์แก้ไขสินค้านี้")
            return redirect('petjoy:product-list')

        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # ✔ แบบ A: แสดงข้อความบนหน้า edit ทันที ไม่ redirect
        messages.success(self.request, "✔ แก้ไขสินค้าเรียบร้อยแล้ว")

        self.object = form.save()
        return self.render_to_response(self.get_context_data(form=form))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['entrepreneur'] = self.request.user.entrepreneur
        ctx['categories'] = Category.objects.all()
        ctx['product'] = self.get_object()
        return ctx



class ProductDeleteView(DeleteView):
    model = Product
    template_name = 'petjoy/products/product_confirm_delete.html'
    success_url = reverse_lazy('petjoy:product-list')

    def dispatch(self, request, *args, **kwargs):
        # ตรวจสอบสิทธิ์: ต้องเป็นผู้ประกอบการเท่านั้น
        if not request.user.is_authenticated or not hasattr(request.user, 'entrepreneur'):
            messages.error(request, 'คุณต้องเป็นผู้ประกอบการและล็อกอินก่อนลบสินค้า')
            return redirect('petjoy:login')

        # ตรวจสอบว่าเป็นเจ้าของสินค้าหรือไม่
        obj = self.get_object()
        if obj.owner is None or obj.owner.user_id != request.user.id:
            messages.error(request, 'คุณไม่มีสิทธิ์ลบสินค้านี้')
            return redirect('petjoy:product-list')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """
        ส่งข้อมูล entrepreneur เข้า template ด้วย
        เพื่อให้ Sidebar แสดงชื่อร้าน รูปโปรไฟล์ และเมนูด้านซ้ายได้ถูกต้อง
        """
        ctx = super().get_context_data(**kwargs)
        ctx['entrepreneur'] = self.request.user.entrepreneur
        return ctx




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
    # paginate 15 per page
    per_page = 15
    paginator = Paginator(products, per_page)
    page_number = request.GET.get('page') or 1
    page_obj = paginator.get_page(page_number)
    # If partial requested (AJAX), return only the grid fragment so JS can update
    if request.GET.get('partial') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.template.loader import render_to_string
        html = render_to_string('petjoy/partials/food_products_grid.html', {
            'products': page_obj,
            'page_obj': page_obj,
            'paginator': paginator,
            'selected_type': 'cat',
        })
        from django.http import HttpResponse
        return HttpResponse(html)

    return render(request, 'petjoy/cat_products.html', {'products': page_obj, 'page_obj': page_obj, 'paginator': paginator})
# สำหรับหน้าสินค้าสุนัข (ลูกค้าทั่วไป)
def dog_products_view(request):
    dog_category = Category.objects.filter(name__iexact='dog').first()
    products = Product.objects.filter(category=dog_category) if dog_category else Product.objects.none()
    # paginate 15 per page
    per_page = 15
    paginator = Paginator(products, per_page)
    page_number = request.GET.get('page') or 1
    page_obj = paginator.get_page(page_number)
    # If partial requested (AJAX), return only the grid fragment so JS can update
    if request.GET.get('partial') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.template.loader import render_to_string
        html = render_to_string('petjoy/partials/food_products_grid.html', {
            'products': page_obj,
            'page_obj': page_obj,
            'paginator': paginator,
            'selected_type': 'dog',
        })
        from django.http import HttpResponse
        return HttpResponse(html)

    return render(request, 'petjoy/dog_products.html', {'products': page_obj, 'page_obj': page_obj, 'paginator': paginator})


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

    # Paginate results: show ~3 rows worth of items per page (assume 4 columns per row)
    per_page = 15
    paginator = Paginator(products, per_page)
    page_number = request.GET.get('page') or 1
    page_obj = paginator.get_page(page_number)

    # If partial requested (AJAX), return only the grid fragment
    if request.GET.get('partial') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from django.template.loader import render_to_string
        html = render_to_string('petjoy/partials/food_products_grid.html', {
            'products': page_obj,
            'page_obj': page_obj,
            'paginator': paginator,
            'selected_type': typ_raw,
        })
        from django.http import HttpResponse
        return HttpResponse(html)

    return render(request, 'petjoy/food_products.html', {
        'products': page_obj,
        'selected_type': typ_raw,
        'page_obj': page_obj,
        'paginator': paginator,
    })



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

@login_required
def orders_list(request):
    entrepreneur = request.user.entrepreneur

    orders = Order.objects.filter(
        entrepreneur=entrepreneur
    ).order_by('-created_at')

    context = {
        "entrepreneur": entrepreneur,
        "orders": orders,

        # ค่าไว้ใช้ในส่วนสรุปบนสุด
        "shipping_count": orders.filter(status="delivering").count(),
        "success_count": orders.filter(status="success").count(),
        "canceled_count": orders.filter(status="canceled").count() if hasattr(Order, 'canceled') else 0,

        # - 5 orders ล่าสุด
        "recent_orders": orders[:5],
    }

    return render(request, "petjoy/entrepreneur/orders_list.html", context)
@login_required
def orders_detail(request, order_id):
    entrepreneur = request.user.entrepreneur
    order = get_object_or_404(Order, id=order_id, entrepreneur=entrepreneur)

    return render(request, "petjoy/entrepreneur/orders_detail.html", {
        "entrepreneur": entrepreneur,
        "order": order
    })


@login_required
def update_order_status(request, order_id):
    entrepreneur = request.user.entrepreneur
    order = get_object_or_404(Order, id=order_id, entrepreneur=entrepreneur)

    if request.method == "POST":
        new_status = request.POST.get("status")
        order.status = new_status
        order.save()
        messages.success(request, "อัปเดตสถานะคำสั่งซื้อเรียบร้อยแล้ว!")
        return redirect("petjoy:orders-detail", order_id=order_id)

    return redirect("petjoy:orders-list")