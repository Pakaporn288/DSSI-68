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
from django.db import transaction
from django.forms import Form
from django.shortcuts import get_object_or_404
from .models import Order, OrderItem, ChatRoom, ChatMessage, Entrepreneur
from django.template.loader import render_to_string
from petjoy.models import Order
from .models import Review, ReviewReply

logger = logging.getLogger(__name__)

def homepage(request):
    products = Product.objects.order_by('?')[:4]  # 👈 สุ่ม 6 ชิ้น
    return render(request, 'petjoy/homepage.html', {
        'products': products,
    })

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

@login_required
def order_detail_customer(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = order.items.all()
    return render(request, "petjoy/order_detail_customer.html", {
        "order": order,
        "items": items
    })

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

def notification_list(request):
    if not request.user.is_authenticated:
        return redirect("petjoy:login")

    # ใช้วิธีเดียวกับ order_history (ชื่อ + เบอร์)
    addresses = Address.objects.filter(user=request.user)
    q = Q()
    for addr in addresses:
        q |= Q(customer_name=addr.full_name, customer_phone=addr.phone)

    orders = (
        Order.objects
        .filter(q)
        .prefetch_related('items__product')
        .order_by('-created_at')
    )

    # สร้าง display_title ให้แต่ละ order
    for order in orders:
        items = order.items.all()
        if items.exists():
            first_product = items.first().product.name
            count = items.count()

            if count > 1:
                order.display_title = f"{first_product} และอีก {count - 1} รายการ"
            else:
                order.display_title = first_product
        else:
            order.display_title = "คำสั่งซื้อของคุณ"

    # 🔔 ถือว่าเข้ามาอ่านแจ้งเตือนแล้ว
    orders.filter(has_unread_status_update=True).update(
        has_unread_status_update=False
    )

    return render(request, "petjoy/notification_list.html", {
        "orders": orders
    })

# แก้ไขฟังก์ชัน review_product ใน views.py
@login_required
def review_product(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    items = order.items.all()

    if request.method == "POST":
        rating = request.POST.get("rating")
        comment = request.POST.get("comment")
        
        for item in items:
            # สร้างรีวิว
            Review.objects.create(
                user=request.user,
                product=item.product,
                order=order,
                rating=rating,
                comment=comment
            )
        
        # เมื่อรีวิวเสร็จ ให้ตั้งค่าว่า Order นี้รีวิวแล้ว (สมมติว่าใช้ field field หนึ่งใน Order หรือตรวจสอบจาก Review model)
        # ในที่นี้เราจะส่ง Success Message ไปให้ SweetAlert ใน Template ทำงาน
        messages.success(request, "บันทึกรีวิวเรียบร้อยแล้ว ขอบคุณที่ใช้บริการค่ะ! 🐾", extra_tags='review_success')
        
        return redirect("petjoy:notification_list") # กลับไปหน้าแจ้งเตือน

    return render(request, "petjoy/review_form.html", {
        "order": order,
        "items": items
    })

@login_required
def reply_review(request, review_id):
    review = get_object_or_404(Review, id=review_id)

    entrepreneur = get_object_or_404(
        Entrepreneur,
        user=request.user
    )

    if hasattr(review, "reply"):
        return redirect("petjoy:entrepreneur_reviews")

    if request.method == "POST":
        message = request.POST.get("reply")

        if message:
            ReviewReply.objects.create(
                review=review,
                entrepreneur=entrepreneur,
                message=message
            )

            # 🔔 แจ้งเตือนลูกค้าผ่าน Order
            if review.order:
                review.order.has_unread_status_update = True
                review.order.save()

            messages.success(
                request,
                "ตอบรีวิวเรียบร้อยแล้ว"
            )

    return redirect("petjoy:entrepreneur_reviews")



@login_required
def order_history(request):
    # เอาที่อยู่ทั้งหมดของ user
    user_addresses = Address.objects.filter(user=request.user)

    # เตรียม list สำหรับ match ตามชื่อ + เบอร์โทร
    name_phone_pairs = []
    for a in user_addresses:
        name_phone_pairs.append((a.full_name, a.phone))

    # หา orders ที่มีชื่อและเบอร์ตรงกันกับ address ของ user
    from django.db.models import Q

    q = Q()
    for name, phone in name_phone_pairs:
        # ใช้ Q เพื่อรวมเงื่อนไข OR
        q |= (Q(customer_name=name) & Q(customer_phone=phone))

    orders = Order.objects.filter(q).order_by("-id")

    return render(request, "petjoy/order_history.html", {
        "orders": orders
    })

@login_required(login_url='petjoy:login')
def checkout_view(request):

    # STEP 1 — แสดงสินค้าในตะกร้าที่เลือก
    if request.method == 'GET' and 'selected_items' in request.GET:
        selected_item_ids = request.GET.getlist('selected_items')

        if not selected_item_ids:
            messages.error(request, 'กรุณาเลือกสินค้าที่ต้องการสั่งซื้อ')
            return redirect('petjoy:cart-detail')

        cart_items = CartItem.objects.filter(id__in=selected_item_ids, user=request.user)

        if not cart_items.exists():
            messages.error(request, 'ไม่พบสินค้าที่เลือกในตะกร้าของคุณ')
            return redirect('petjoy:cart-detail')

        total_price = sum(item.total_price for item in cart_items)

        addresses = Address.objects.filter(user=request.user).order_by('-is_default')
        if not addresses.exists():
            messages.warning(request, 'กรุณาเพิ่มที่อยู่จัดส่งก่อนดำเนินการสั่งซื้อ')
            return redirect('petjoy:address_add')

        # แยกสินค้าเป็นร้าน ๆ
        items_by_entrepreneur = {}
        for item in cart_items:
            owner = item.product.owner
            if owner:
                items_by_entrepreneur.setdefault(owner, []).append(item)

        # เก็บข้อมูลไว้ใน session
        request.session['checkout_items_data'] = {
            'item_ids': [str(x) for x in selected_item_ids],
            'total_price': float(total_price),
        }

        return render(request, 'petjoy/checkout.html', {
            'step': 1,
            'items_by_entrepreneur': items_by_entrepreneur,
            'total_price': total_price,
            'addresses': addresses,
            'selected_item_ids_str': ','.join(selected_item_ids)
        })

    # STEP 2 — เลือกที่อยู่และวิธีชำระเงิน
    if request.method == 'POST' and request.POST.get('checkout_step') == "1":

        address_id = request.POST.get("address_id")
        selected_item_ids_str = request.POST.get("selected_item_ids_str") or ''

        if not address_id or not selected_item_ids_str:
            messages.error(request, 'ข้อมูลไม่สมบูรณ์ หรือ Session หมดอายุ')
            return redirect('petjoy:cart-detail')

        address = get_object_or_404(Address, id=address_id, user=request.user)

        checkout_data = request.session.get('checkout_items_data')
        if not checkout_data:
            messages.error(request, 'Session หมดอายุ กรุณาเริ่มใหม่')
            return redirect('petjoy:cart-detail')

        # ตรวจสอบความตรงกันของสินค้า
        if set(map(str, checkout_data['item_ids'])) != set(selected_item_ids_str.split(',')):
            messages.error(request, 'เกิดข้อผิดพลาดในการประมวลผลคำสั่งซื้อ')
            return redirect('petjoy:cart-detail')

        request.session['checkout_address_id'] = address_id

        # โหลดสินค้าใหม่
        item_ids = selected_item_ids_str.split(',')
        cart_items = CartItem.objects.filter(id__in=item_ids, user=request.user)

        items_by_entrepreneur = {}
        for item in cart_items:
            owner = item.product.owner
            if owner:
                items_by_entrepreneur.setdefault(owner, []).append(item)

        return render(request, "petjoy/checkout.html", {
            "step": 2,
            "total_price": checkout_data["total_price"],
            "address": address,
            "items_by_entrepreneur": items_by_entrepreneur,
        })

    # STEP 3 — ยืนยันการสั่งซื้อและสร้าง Order จริง
    if request.method == "POST" and request.POST.get("checkout_step") == "2":

        payment_method = request.POST.get("payment_method")
        payment_slip = request.FILES.get("payment_slip")

        if not payment_method:
            messages.error(request, "กรุณาเลือกวิธีการชำระเงิน")
            return redirect("petjoy:cart-detail")

        # ถ้าชำระด้วยโอนเงิน ต้องมีสลิป
        if payment_method == "bank_transfer" and not payment_slip:
            messages.error(request, "กรุณาแนบสลิปการโอนเงิน")
            return redirect("petjoy:cart-detail")

        address_id = request.session.get("checkout_address_id")
        item_ids = request.session.get("checkout_items_data", {}).get("item_ids")
        total_price_raw = request.session.get("checkout_items_data", {}).get("total_price")

        if not address_id or not item_ids:
            messages.error(request, "Session หมดอายุ กรุณาเริ่มใหม่")
            return redirect("petjoy:cart-detail")

        address = get_object_or_404(Address, id=address_id, user=request.user)
        cart_items = CartItem.objects.filter(id__in=item_ids, user=request.user)

        if not cart_items.exists():
            messages.error(request, "ไม่พบสินค้าในตะกร้าที่เลือก")
            return redirect("petjoy:cart-detail")

        with transaction.atomic():

            # แยกร้าน
            items_by_entrepreneur = {}
            for item in cart_items:
                owner = item.product.owner
                if owner:
                    items_by_entrepreneur.setdefault(owner, []).append(item)

            created_orders = []

            for entrepreneur, items in items_by_entrepreneur.items():

                shop_total_price = sum(item.total_price for item in items)

                order_status = "paid" if payment_method == "bank_transfer" else "waiting"

                # ⭐ สร้างคำสั่งซื้อ
                order = Order.objects.create(
                    entrepreneur=entrepreneur,
                    customer_name=address.full_name,
                    customer_phone=address.phone,
                    customer_address=f"{address.address_line} {address.subdistrict} {address.district} {address.province} {address.zipcode}",
                    total_price=shop_total_price,
                    status=order_status,
                    slip_image=payment_slip if payment_method == "bank_transfer" else None,  # ⭐ บันทึกสลิป
                )

                # ⭐ สร้าง OrderItem
                for cart_item in items:
                    OrderItem.objects.create(
                        order=order,
                        product=cart_item.product,
                        quantity=cart_item.quantity,
                        price=cart_item.product.price
                    )

                created_orders.append(order)

            # ลบสินค้าในตะกร้า
            cart_items.delete()

            # ล้าง session
            request.session.pop("checkout_items_data", None)
            request.session.pop("checkout_address_id", None)

        return render(request, "petjoy/checkout.html", {
            "step": 3,
            "orders": created_orders,
            "total_price": total_price_raw,
            "address": address,
        })

    # fallback
    messages.error(request, "กรุณาเลือกสินค้าที่ต้องการสั่งซื้อจากตะกร้า")
    return redirect("petjoy:cart-detail")


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
    """
    รองรับทั้งแบบหน้าเต็ม (POST form) และ AJAX (JSON) สำหรับเพิ่มที่อยู่
    AJAX: รับ JSON POST, ตอบกลับเป็น JSON { success: True, address: {...} }
    """
    if request.method == "POST":
        # ถ้ามาเป็น JSON/AJAX
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.content_type == 'application/json':
            try:
                payload = json.loads(request.body.decode('utf-8'))
            except Exception:
                return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
            # basic validation
            required = ['full_name', 'phone', 'address_line', 'subdistrict', 'district', 'province']
            if not all(payload.get(k) for k in required):
                return JsonResponse({'success': False, 'error': 'กรุณากรอกข้อมูลให้ครบถ้วน'}, status=400)
            # create address
            addr = Address.objects.create(
                user=request.user,
                full_name=payload.get('full_name'),
                phone=payload.get('phone'),
                address_line=payload.get('address_line'),
                subdistrict=payload.get('subdistrict'),
                district=payload.get('district'),
                province=payload.get('province'),
                zipcode=payload.get('zipcode') or ''
            )
            return JsonResponse({
                'success': True,
                'address': {
                    'id': addr.id,
                    'full_name': addr.full_name,
                    'phone': addr.phone,
                    'address_line': addr.address_line,
                    'subdistrict': addr.subdistrict,
                    'district': addr.district,
                    'province': addr.province,
                    'zipcode': addr.zipcode,
                    'is_default': addr.is_default,
                }
            })
        # ถ้ามาเป็น form submit ปกติ (ไม่ถูกปรับ)
        Address.objects.create(
            user=request.user,
            full_name=request.POST['full_name'],
            phone=request.POST['phone'],
            address_line=request.POST['address_line'],
            subdistrict=request.POST['subdistrict'],
            district=request.POST['district'],
            province=request.POST['province'],
            zipcode=request.POST.get('zipcode',''),
        )
        return redirect('petjoy:address_list')

    # GET -> แสดงฟอร์ม (ปกติ)
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


@login_required
def entrepreneur_profile_settings(request):

    entrepreneur = request.user.entrepreneur  # ดึงโปรไฟล์ร้านของ user

    if request.method == "POST":

        # หมวด 1: TAX
        if "save_tax" in request.POST:
            entrepreneur.tax_id = request.POST.get("tax_id")
            entrepreneur.save()
            messages.success(request, "บันทึกข้อมูลภาษีแล้ว", extra_tags="tax")

        # หมวด 2: Address
        if "save_address" in request.POST:
            entrepreneur.shop_address = request.POST.get("shop_address")
            entrepreneur.save()
            messages.success(request, "บันทึกที่อยู่ร้านแล้ว", extra_tags="address")

        # หมวด 3: Bank Info
        if "save_bank" in request.POST:
            entrepreneur.bank_name = request.POST.get("bank_name")
            entrepreneur.account_name = request.POST.get("account_name")
            entrepreneur.account_number = request.POST.get("account_number")

            if request.FILES.get("bank_book_copy"):
                entrepreneur.bank_book_copy = request.FILES["bank_book_copy"]

            entrepreneur.save()
            messages.success(request, "บันทึกข้อมูลบัญชีธนาคารแล้ว", extra_tags="bank")

        # หมวด 4: ID Card
        if "save_idcard" in request.POST:
            if request.FILES.get("id_card_copy"):
                entrepreneur.id_card_copy = request.FILES["id_card_copy"]
            entrepreneur.save()
            messages.success(request, "บันทึกสำเนาบัตรประชาชนแล้ว", extra_tags="idcard")

    # 🎯 ต้องส่ง entrepreneur เพิ่มเข้าไป
    return render(request, "petjoy/entrepreneur/entrepreneur_profile_settings.html", {
        "profile": entrepreneur,
        "entrepreneur": entrepreneur,      # ⭐ สำคัญที่สุด
        "is_entrepreneur": True,           # ใช้กับ sidebar ถ้าจำเป็น
    })

@login_required(login_url=reverse_lazy('petjoy:login'))
def entrepreneur_reviews(request):
    # ป้องกัน user ทั่วไป
    if not hasattr(request.user, 'entrepreneur'):
        messages.error(request, "คุณต้องเป็นผู้ประกอบการก่อน")
        return redirect('petjoy:login')

    entrepreneur = request.user.entrepreneur

    # 👉 base queryset (ของเดิม)
    reviews = Review.objects.filter(
        product__owner=entrepreneur
    ).select_related(
        'product',
        'user'
    ).prefetch_related(
        'reply'
    )

    # =========================
    # 🔍 FILTER LOGIC (เพิ่ม)
    # =========================
    filter_type = request.GET.get('filter', 'all')

    if filter_type == 'unreplied':
        # ยังไม่ตอบ
        reviews = reviews.filter(reply__isnull=True).order_by('-created_at')

    elif filter_type == 'replied_latest':
        # ตอบแล้ว เรียงตามเวลาตอบล่าสุด
        reviews = reviews.filter(reply__isnull=False).order_by('-reply__created_at')

    else:
        # all (ค่า default)
        reviews = reviews.order_by('-created_at')

    return render(request, 'petjoy/entrepreneur/reviews.html', {
        'entrepreneur': entrepreneur,
        'reviews': reviews,
        'current_filter': filter_type,  # (เผื่อเอาไปทำ active state)
    })


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
def order_detail(request, order_id):
    entrepreneur = request.user.entrepreneur

    # ป้องกันไม่ให้ร้านอื่นเข้ามาดู order ของร้านนี้
    order = get_object_or_404(Order, id=order_id, entrepreneur=entrepreneur)

    if request.method == "POST":
        new_status = request.POST.get("status")
        order.status = new_status
        order.has_unread_status_update = True  # 🔔 บรรทัดแจ้งเตือนลูกค้า (เพิ่มตรงนี้)
        order.save()
        messages.success(request, "อัปเดตสถานะคำสั่งซื้อเรียบร้อยแล้ว!")
        return redirect("petjoy:orders-detail", order_id=order.id)

    return render(request, "petjoy/entrepreneur/orders_detail.html", {
        "order": order,
        "entrepreneur": entrepreneur,
    })


@login_required
def update_order_status(request, order_id):
    entrepreneur = request.user.entrepreneur
    order = get_object_or_404(Order, id=order_id, entrepreneur=entrepreneur)

    if request.method == "POST":
        new_status = request.POST.get("status")
        order.status = new_status

        # 🔔 บรรทัดแจ้งเตือนลูกค้า (เพิ่มตรงนี้)
        order.has_unread_status_update = True

        order.save()
        messages.success(request, "อัปเดตสถานะคำสั่งซื้อเรียบร้อยแล้ว!")
        return redirect("petjoy:orders-detail", order_id=order_id)

    return redirect("petjoy:orders-list")


@login_required
def delete_chat(request, room_id):
    """ฟังก์ชันลบห้องแชท"""
    if request.method == 'POST':
        room = get_object_or_404(ChatRoom, id=room_id)
        
        # ตรวจสอบสิทธิ์ว่าเป็นเจ้าของห้องจริงไหม
        is_owner = (request.user == room.customer) or \
                   (hasattr(request.user, 'entrepreneur') and request.user.entrepreneur == room.entrepreneur)
        
        if is_owner:
            room.delete()
            messages.success(request, "ลบห้องแชทเรียบร้อยแล้ว")
        else:
            messages.error(request, "คุณไม่มีสิทธิ์ลบห้องแชทนี้")
            
    return redirect('petjoy:chat_list')



@login_required
def start_chat_view(request, entrepreneur_id):
    """ฟังก์ชันสำหรับเริ่มแชท (กดปุ่ม 'แชทเลย' จากหน้าสินค้า)"""
    from .models import Entrepreneur # import เฉพาะจุดเพื่อเลี่ยง circular import
    
    # 1. หาผู้ประกอบการเป้าหมาย
    entrepreneur = get_object_or_404(Entrepreneur, id=entrepreneur_id)
    
    # 2. ป้องกันไม่ให้แชทกับตัวเอง (กรณี Login เป็นเจ้าของร้านนั้นอยู่)
    if hasattr(request.user, 'entrepreneur') and request.user.entrepreneur.id == entrepreneur_id:
        messages.error(request, "คุณไม่สามารถแชทกับร้านค้าของตัวเองได้")
        return redirect('petjoy:homepage') # หรือ redirect กลับไปหน้าเดิม

    # 3. หาห้องแชทเดิม หรือ สร้างใหม่ถ้ายังไม่มี
    room, created = ChatRoom.objects.get_or_create(
        customer=request.user,
        entrepreneur=entrepreneur
    )
    
    # 4. ส่งไปที่หน้าห้องแชท
    return redirect('petjoy:chat_room', room_id=room.id)

@login_required
def chat_list(request):
    """แสดงรายชื่อห้องแชททั้งหมด"""
    
    # 1. ดึงห้องแชทที่ User เกี่ยวข้อง (เป็นลูกค้า หรือ เป็นเจ้าของร้าน)
    rooms = ChatRoom.objects.filter(
        Q(customer=request.user) | 
        Q(entrepreneur__user=request.user)
    ).distinct().order_by('-id') # เรียงตามห้องล่าสุด
    
    # 2. ตรวจสอบว่าเป็นผู้ประกอบการหรือไม่
    is_entrepreneur = hasattr(request.user, 'entrepreneur')

    context = {
        'rooms': rooms,
        'current_user': request.user,
        'is_entrepreneur': is_entrepreneur,
        'entrepreneur': request.user.entrepreneur if is_entrepreneur else None,
    }

    # 3. เลือก Template ตามประเภทผู้ใช้
    if is_entrepreneur:
        # *** ชี้ไปที่พาธ Template สำหรับผู้ประกอบการโดยเฉพาะ ***
        return render(request, 'petjoy/entrepreneur/entrepreneur_chat_list.html', context)
    else:
        # ใช้ Template ของลูกค้าที่มีอยู่
        return render(request, 'petjoy/chat_list.html', context)


# ... (delete_chat และ start_chat_view ไม่มีการเปลี่ยนแปลง)


@login_required
def chat_list(request):
    """แสดงรายชื่อห้องแชททั้งหมดสำหรับลูกค้าเท่านั้น"""
    # ตรวจสอบว่าไม่ใช่ผู้ประกอบการ
    if hasattr(request.user, 'entrepreneur'):
        return redirect('petjoy:entrepreneur-chat-list') # ส่งไปยังหน้าของร้านค้า
        
    rooms = ChatRoom.objects.filter(customer=request.user).order_by('-id')
    
    return render(request, 'petjoy/chat_list.html', {
        'rooms': rooms,
        'current_user': request.user
    })

@login_required
def chat_room(request, room_id):
    """ฟังก์ชันแสดงหน้าห้องแชทสำหรับลูกค้าเท่านั้น"""
    room = get_object_or_404(ChatRoom, id=room_id, customer=request.user)
    
    # ถ้าเป็นเจ้าของร้านเข้ามา ให้ redirect ไปใช้หน้าของเจ้าของร้าน
    if hasattr(request.user, 'entrepreneur') and request.user.entrepreneur == room.entrepreneur:
         return redirect('petjoy:entrepreneur-chat-room', room_id=room.id)

    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        # ไม่มี file attachment สำหรับลูกค้าในหน้าเดิมนี้
        if message_text:
            ChatMessage.objects.create(
                room=room,
                sender=request.user,
                message=message_text
            )
        return redirect('petjoy:chat_room', room_id=room.id)

    messages_list = room.chatmessage_set.all().order_by('id')
    
    return render(request, 'petjoy/chat_room.html', {
        'room': room,
        'messages': messages_list,
        'current_user': request.user
    })



@login_required
def chat_list(request):
    """แสดงรายชื่อห้องแชททั้งหมดสำหรับลูกค้าเท่านั้น"""
    # ถ้าเป็นผู้ประกอบการเข้ามา ให้ส่งไปยังหน้าของผู้ประกอบการ
    if hasattr(request.user, 'entrepreneur'):
        return redirect('petjoy:entrepreneur-chat-list') 
        
    rooms = ChatRoom.objects.filter(customer=request.user).order_by('-id')
    
    return render(request, 'petjoy/chat_list.html', {
        'rooms': rooms,
        'current_user': request.user
    })

@login_required
def chat_room(request, room_id):
    """ฟังก์ชันแสดงหน้าห้องแชทสำหรับลูกค้าเท่านั้น"""
    # ดึงห้องแชทโดยตรวจสอบว่าเป็นลูกค้าในห้องนี้หรือไม่
    room = get_object_or_404(ChatRoom, id=room_id, customer=request.user)
    
    # ถ้าเป็นเจ้าของร้านเข้ามา (แม้จะผ่าน URL ของลูกค้า) ให้ redirect ไปใช้หน้าของเจ้าของร้าน
    if hasattr(request.user, 'entrepreneur') and request.user.entrepreneur == room.entrepreneur:
         return redirect('petjoy:entrepreneur-chat-room', room_id=room.id)

    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        
        if message_text:
            ChatMessage.objects.create(
                room=room,
                sender=request.user,
                message=message_text
            )
        return redirect('petjoy:chat_room', room_id=room.id)

    # ⭐ แก้ไขการเรียกใช้: ใช้ room.messages.all() ตาม related_name ใน models.py ⭐
    messages_list = room.messages.all().order_by('id') 
    
    return render(request, 'petjoy/chat_room.html', {
        'room': room,
        'messages': messages_list,
        'current_user': request.user
    })


# ==========================================================
# ⭐ CHAT FUNCTIONS: ENTREPRENEUR (ฟังก์ชันสำหรับผู้ประกอบการ) ⭐
# ==========================================================

@login_required
def entrepreneur_chat_list(request):
    """แสดงรายชื่อห้องแชททั้งหมดสำหรับผู้ประกอบการเท่านั้น"""
    if not hasattr(request.user, 'entrepreneur'):
        return redirect('petjoy:chat_list') # หากไม่ใช่ผู้ประกอบการ ให้ใช้หน้าของลูกค้า

    entrepreneur = request.user.entrepreneur
    
    rooms = ChatRoom.objects.filter(entrepreneur=entrepreneur).order_by('-id')

    context = {
        'rooms': rooms,
        'current_user': request.user,
        'entrepreneur': entrepreneur,
    }

    # ชี้ไปที่ Template ในโฟลเดอร์ entrepreneur/
    return render(request, 'petjoy/entrepreneur/entrepreneur_chat_list.html', context)


@login_required
def entrepreneur_chat_room(request, room_id):
    """ฟังก์ชันแสดงหน้าห้องแชทสำหรับผู้ประกอบการเท่านั้น"""
    # ดึงผู้ประกอบการที่ล็อกอิน และตรวจสอบว่าห้องแชทนี้เป็นของร้านตัวเอง
    entrepreneur = get_object_or_404(Entrepreneur, user=request.user)
    room = get_object_or_404(ChatRoom, id=room_id, entrepreneur=entrepreneur)
    
    # 2. จัดการการส่งข้อความ (POST) พร้อมรองรับไฟล์แนบ
    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        uploaded_file = request.FILES.get('attachment') 

        if message_text or uploaded_file: 
            
            if uploaded_file:
                # Placeholder: สร้างข้อความแจ้งว่ามีการแนบไฟล์
                file_info = f"[ไฟล์แนบ: {uploaded_file.name}]"
                if message_text:
                    message_text += f"\n{file_info}"
                else:
                    message_text = file_info
                
            ChatMessage.objects.create(
                room=room,
                sender=request.user,
                message=message_text
            )
            return redirect('petjoy:entrepreneur-chat-room', room_id=room.id)

    # 3. ดึงข้อความเก่ามาแสดง
    # ⭐ แก้ไขการเรียกใช้: ใช้ room.messages.all() ตาม related_name ใน models.py ⭐
    messages_list = room.messages.all().order_by('id') 
    
    context = {
        'room': room,
        'messages': messages_list,
        'current_user': request.user,
        'entrepreneur': entrepreneur,
    }

    # ชี้ไปที่ Template ในโฟลเดอร์ entrepreneur/
    return render(request, 'petjoy/entrepreneur/entrepreneur_chat_room.html', context)

@login_required
def entrepreneur_chat_delete(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    # ป้องกันผู้ใช้ลบห้องของคนอื่น
    if request.user != room.entrepreneur.user:
        messages.error(request, "คุณไม่มีสิทธิ์ลบแชทนี้")
        return redirect('petjoy:entrepreneur-chat-list')

    # ลบข้อความทั้งหมดในห้อง
    ChatMessage.objects.filter(room=room).delete()

    # ลบตัวห้องแชท
    room.delete()

    messages.success(request, "ลบแชทเรียบร้อยแล้ว")
    return redirect('petjoy:entrepreneur-chat-list')

@login_required
@require_POST
def report_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    reason = request.POST.get('reason')
    details = request.POST.get('details', '')

    if not reason:
        return JsonResponse({'success': False, 'error': 'กรุณาระบุเหตุผล'}, status=400)

    from .models import ProductReport
    ProductReport.objects.create(
        user=request.user,
        product=product,
        reason=reason,
        details=details
    )

    return JsonResponse({'success': True, 'message': 'ส่งรายงานให้เจ้าหน้าที่เรียบร้อยแล้ว'})