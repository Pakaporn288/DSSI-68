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
from .models import QuickReply
from django.utils import timezone
from django.db.models.functions import TruncDate
from django.db.models import Sum, Count, F
from datetime import timedelta
from django.shortcuts import render, redirect
from .models import Entrepreneur, Order
from django.db.models.functions import Coalesce
from .models import ProductReport
from django.urls import reverse
from django.contrib.auth.models import User
from .forms import RegisterForm
from .models import CustomerAdminChatRoom, CustomerAdminChatMessage

logger = logging.getLogger(__name__)

def homepage(request):
    products = Product.objects.order_by('?')[:4]  # 👈 สุ่ม 6 ชิ้น (ตามคอมเมนต์เดิมในไฟล์)
    categories = Category.objects.all().order_by('id')

    return render(request, 'petjoy/homepage.html', {
        'products': products,
        'categories': categories,
    })

def ask_ai_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message')

            if not user_message:
                return JsonResponse({'error': 'No message provided'}, status=400)

            # --- เงื่อนไขใหม่: เช็คว่าเป็นสมาชิกหรือไม่ ---
            if request.user.is_authenticated:
                # ถ้า Login -> ส่ง ID ไปให้ AI จำประวัติ
                user_id = str(request.user.id)
            else:
                # ถ้าไม่ Login -> ส่ง None (AI จะไม่จำประวัติ)
                user_id = None

            # เรียก AI
            ai_reply = get_ai_response(user_message, user_id)

            # --- การบันทึก Database ---
            # บันทึกเฉพาะคนที่ Login แล้วเท่านั้น (ตามที่คุณขอ)
            if request.user.is_authenticated:
                # ตรวจสอบว่า Model คุณชื่อ ChatMessage หรือ ChatHistory
                # อันนี้อ้างอิงจากที่คุณเคยส่งไฟล์ models.py มา
                ChatMessage.objects.create(
                    sender=request.user, # หรือ user=request.user แล้วแต่ชื่อ field
                    message=user_message,
                    # ถ้า Model คุณไม่มี field เก็บคำตอบ AI ให้ลบบรรทัดล่างทิ้ง หรือต้องเพิ่ม field ใน models.py
                    # response=ai_reply 
                )

            return JsonResponse({'reply': ai_reply})

        except Exception as e:
            print(f"Error in ask_ai_view: {e}")
            return JsonResponse({'reply': 'ขออภัยค่ะ ระบบมีปัญหาเล็กน้อย ลองใหม่อีกครั้งนะคะ'}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


def logout_view(request):
    logout(request)
    messages.info(request, "คุณได้ออกจากระบบแล้ว")
    return redirect("petjoy:homepage")


def register_view(request):
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

    reviews = (
        product.reviews
        .select_related('user')
        .prefetch_related('reply')  
        .order_by('-created_at')
    )

    is_out_of_stock = product.stock <= 0 # เช็คสต็อก

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

    # ==============================
    # ✅ เช็คว่าสินค้าหมดหรือไม่
    # ==============================
    if product.stock <= 0:
        messages.error(request, "สินค้าหมด ไม่สามารถเพิ่มลงตะกร้าได้")
        return redirect(request.META.get("HTTP_REFERER", "petjoy:homepage"))

    # ==============================
    # ✅ เช็คว่าจำนวนที่กดเกิน stock หรือไม่
    # ==============================
    if quantity > product.stock:
        messages.error(request, f"สินค้าเหลือเพียง {product.stock} ชิ้น")
        return redirect(request.META.get("HTTP_REFERER", "petjoy:homepage"))

    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        product=product
    )

    # ==============================
    # ✅ ป้องกันกรณีบวกแล้วเกิน stock
    # ==============================
    if created:
        cart_item.quantity = quantity
    else:
        new_quantity = cart_item.quantity + quantity
        if new_quantity > product.stock:
            messages.error(request, f"สินค้าเหลือเพียง {product.stock} ชิ้น")
            return redirect(request.META.get("HTTP_REFERER", "petjoy:homepage"))
        cart_item.quantity = new_quantity

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
    # ดึงข้อมูลออเดอร์ของลูกค้า (ระวังอย่ามี .profile ต่อท้ายนะคะ ให้ใช้ request.user)
    order = get_object_or_404(Order, id=order_id, customer=request.user)
    
    # 🟢 เพิ่มบล็อกนี้เข้าไป เพื่อรอรับคำสั่ง "ขอยกเลิก" จากหน้า HTML
    if request.method == "POST":
        action = request.POST.get("action")
        
        if action == "cancel_by_customer":
            cancel_reason = request.POST.get("cancel_reason")
            
            # เช็คว่าสถานะยังสามารถยกเลิกได้อยู่
            if order.status in ['waiting', 'paid', 'preparing']:
                # เปลี่ยนสถานะเป็น "ขอยกเลิก" (ส่งคำร้องให้ร้านค้า)
                order.status = 'cancel_requested' 
                order.cancel_reason = cancel_reason
                
                # แจ้งเตือนให้ร้านค้ารู้ว่ามีอัปเดต
                order.has_unread_status_update = True 
                order.save()
                
                messages.success(request, 'ส่งคำร้องขอยกเลิกไปยังร้านค้าเรียบร้อยแล้ว กรุณารอการอนุมัติ')
                return redirect('petjoy:order_detail_customer', order_id=order.id)
                
    # โค้ดเดิมของคุณสำหรับแสดงหน้าเว็บ
    return render(request, "petjoy/order_detail_customer.html", {"order": order})

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

    # ดึงคำสั่งซื้อทั้งหมดที่เกี่ยวข้อง และเช็คสถานะสำคัญ
    orders = (
        Order.objects
        .filter(q)
        .prefetch_related('items__product', 'reviews')
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

    # 🔔 อัปเดตสถานะว่าอ่านแล้ว เฉพาะรายการที่ยังไม่ได้อ่าน
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

# views.py

@login_required(login_url='petjoy:login')
def checkout_view(request):

    # ==================================================================
    # 🛠️ Helper Function: ช่วยจัดกลุ่มสินค้าและคำนวณราคา (ใช้ซ้ำได้)
    # ==================================================================
    def prepare_checkout_data(cart_items):
        checkout_shops = []
        grand_total = 0
        
        # 1. จัดกลุ่มสินค้าตามร้านค้า
        grouped = {}
        for item in cart_items:
            owner = item.product.owner
            if owner:
                if owner not in grouped:
                    grouped[owner] = []
                grouped[owner].append(item)
        
        # 2. คำนวณยอดเงินของแต่ละร้าน (ค่าสินค้า + ค่าส่ง)
        for owner, items in grouped.items():
            shop_subtotal = sum(item.total_price for item in items) # เฉพาะค่าสินค้า
            shipping_cost = getattr(owner, 'shipping_cost', 0) or 0 # ค่าส่ง
            
            shop_total = float(shop_subtotal) + float(shipping_cost) # ยอดสุทธิร้านนี้
            grand_total += shop_total # บวกเข้ายอดรวมทั้งหมด

            checkout_shops.append({
                'owner': owner,
                'items': items,
                'subtotal': shop_subtotal,
                'shipping': shipping_cost,
                'shop_total': shop_total
            })
            
        return checkout_shops, grand_total

    # ==================================================================
    # STEP 1 — แสดงสินค้าและที่อยู่
    # ==================================================================
    if request.method == 'GET' and 'selected_items' in request.GET:
        selected_item_ids = request.GET.getlist('selected_items')

        if not selected_item_ids:
            messages.error(request, 'กรุณาเลือกสินค้าที่ต้องการสั่งซื้อ')
            return redirect('petjoy:cart-detail')

        cart_items = CartItem.objects.filter(id__in=selected_item_ids, user=request.user)

        if not cart_items.exists():
            messages.error(request, 'ไม่พบสินค้าที่เลือกในตะกร้าของคุณ')
            return redirect('petjoy:cart-detail')

        # ⭐ เรียกใช้ฟังก์ชันคำนวณราคา ⭐
        checkout_shops, grand_total = prepare_checkout_data(cart_items)

        addresses = Address.objects.filter(user=request.user).order_by('-is_default')
        if not addresses.exists():
            messages.warning(request, 'กรุณาเพิ่มที่อยู่จัดส่งก่อนดำเนินการสั่งซื้อ')
            return redirect('petjoy:address_add')

        # เก็บข้อมูลไว้ใน session
        request.session['checkout_items_data'] = {
            'item_ids': [str(x) for x in selected_item_ids],
            'grand_total': grand_total, # เก็บยอดสุทธิ (รวมค่าส่งแล้ว)
        }

        return render(request, 'petjoy/checkout.html', {
            'step': 1,
            'checkout_shops': checkout_shops, # ส่งโครงสร้างข้อมูลใหม่ไป
            'total_price': grand_total,       # ยอดรวมจริงที่รวมค่าส่งแล้ว
            'addresses': addresses,
            'selected_item_ids_str': ','.join(selected_item_ids)
        })

    # ==================================================================
    # STEP 2 — เลือกวิธีชำระเงิน
    # ==================================================================
    if request.method == 'POST' and request.POST.get('checkout_step') == "1":

        address_id = request.POST.get("address_id")
        selected_item_ids_str = request.POST.get("selected_item_ids_str") or ''

        if not address_id or not selected_item_ids_str:
            messages.error(request, 'ข้อมูลไม่สมบูรณ์ หรือ Session หมดอายุ')
            return redirect('petjoy:cart-detail')

        address = get_object_or_404(Address, id=address_id, user=request.user)

        # ตรวจสอบ Session
        checkout_data = request.session.get('checkout_items_data')
        if not checkout_data:
            messages.error(request, 'Session หมดอายุ กรุณาเริ่มใหม่')
            return redirect('petjoy:cart-detail')

        request.session['checkout_address_id'] = address_id

        # ดึงสินค้ามาคำนวณใหม่อีกรอบเพื่อความชัวร์
        item_ids = selected_item_ids_str.split(',')
        cart_items = CartItem.objects.filter(id__in=item_ids, user=request.user)
        
        # ⭐ เรียกใช้ฟังก์ชันคำนวณราคา ⭐
        checkout_shops, grand_total = prepare_checkout_data(cart_items)

        return render(request, "petjoy/checkout.html", {
            "step": 2,
            "total_price": grand_total,
            "address": address,
            "checkout_shops": checkout_shops, # ส่งโครงสร้างข้อมูลใหม่ไป
        })

    # ==================================================================
    # STEP 3 — ยืนยันการสั่งซื้อและสร้าง Order จริง
    # ==================================================================
    if request.method == "POST" and request.POST.get("checkout_step") == "2":

        payment_method = request.POST.get("payment_method")

        if not payment_method:
            messages.error(request, "กรุณาเลือกวิธีการชำระเงิน")
            return redirect("petjoy:cart-detail")

        address_id = request.session.get("checkout_address_id")
        item_ids = request.session.get("checkout_items_data", {}).get("item_ids")
        
        if not address_id or not item_ids:
            messages.error(request, "Session หมดอายุ กรุณาเริ่มใหม่")
            return redirect("petjoy:cart-detail")

        address = get_object_or_404(Address, id=address_id, user=request.user)
        cart_items = CartItem.objects.filter(id__in=item_ids, user=request.user)

        if not cart_items.exists():
            messages.error(request, "ไม่พบสินค้าในตะกร้าที่เลือก")
            return redirect("petjoy:cart-detail")

        try:
            # ⭐ ใช้ฟังก์ชันคำนวณราคา เพื่อเอาข้อมูลมาวนลูปสร้าง Order ⭐
            checkout_shops, grand_total = prepare_checkout_data(cart_items)

            with transaction.atomic():
                
                # Check Stock & Slips
                if payment_method == "bank_transfer":
                    for shop_data in checkout_shops:
                        owner = shop_data['owner']
                        slip_key = f"payment_slip_{owner.id}"
                        if not request.FILES.get(slip_key):
                            raise ValueError(f"กรุณาแนบสลิปการโอนเงินสำหรับร้าน: {owner.store_name}")

                for item in cart_items:
                    if item.product.stock < item.quantity:
                        raise ValueError(f"สินค้า '{item.product.name}' เหลือเพียง {item.product.stock} ชิ้น")

                created_orders = []

                # ⭐ วนลูปสร้าง Order จากข้อมูลที่คำนวณไว้แล้ว ⭐
                for shop_data in checkout_shops:
                    owner = shop_data['owner']
                    items = shop_data['items']
                    final_shop_total = shop_data['shop_total'] # ยอดสุทธิรวมค่าส่งแล้ว
                    shipping_cost = shop_data['shipping']

                    order_status = "paid" if payment_method == "bank_transfer" else "waiting"
                    
                    shop_slip_image = None
                    if payment_method == "bank_transfer":
                        shop_slip_image = request.FILES.get(f"payment_slip_{owner.id}")

                    # Create Order
                    order = Order.objects.create(
                        entrepreneur=owner,
                        customer=request.user,
                        customer_name=address.full_name,
                        customer_phone=address.phone,
                        customer_address=f"{address.address_line} {address.subdistrict} {address.district} {address.province} {address.zipcode}",
                        
                        total_price=final_shop_total,  # ยอดที่ถูกต้อง (สินค้า+ส่ง)
                        shipping_cost=shipping_cost,   # บันทึกค่าส่งไว้ดูเล่น
                        
                        status=order_status,
                        slip_image=shop_slip_image,
                    )

                    # Create Order Items
                    for cart_item in items:
                        OrderItem.objects.create(
                            order=order,
                            product=cart_item.product,
                            quantity=cart_item.quantity,
                            price=cart_item.product.price
                        )
                        # Cut Stock
                        product = cart_item.product
                        product.stock = product.stock - cart_item.quantity
                        product.save()

                    created_orders.append(order)

                # Clear Cart
                cart_items.delete()
                request.session.pop("checkout_items_data", None)
                request.session.pop("checkout_address_id", None)

            return render(request, "petjoy/checkout.html", {
                "step": 3,
                "orders": created_orders,
                "total_price": grand_total, 
                "address": address,
            })

        except ValueError as e:
            messages.error(request, str(e))
            return redirect('petjoy:cart-detail') 
        
        except Exception as e:
            messages.error(request, f"เกิดข้อผิดพลาด: {str(e)}")
            return redirect('petjoy:cart-detail')

    messages.error(request, "การดำเนินการไม่ถูกต้อง")
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
    """
    หน้าลงทะเบียนผู้ประกอบการ
    รองรับทั้งคนที่เป็นสมาชิกแล้ว (Authenticated) และยังไม่เป็นสมาชิก (Anonymous)
    """
    
    # ========================================================
    # กรณีที่ 1: เป็นสมาชิกแล้ว (Logged in User)
    # ========================================================
    if request.user.is_authenticated:
        if hasattr(request.user, 'entrepreneur'):
            messages.info(request, 'คุณมีโปรไฟล์ผู้ประกอบการอยู่แล้ว')
            return redirect('petjoy:entrepreneur-home')

        if request.method == 'POST':
            # รับข้อมูลทั่วไป
            store_name = request.POST.get('store_name')
            owner_name = request.POST.get('owner_name')
            email = request.POST.get('email') or request.user.email
            phone = request.POST.get('phone')
            tax_id = request.POST.get('tax_id')
            shop_address = request.POST.get('shop_address')
            
            # รับข้อมูลธนาคาร
            bank_name = request.POST.get('bank_name')
            account_name = request.POST.get('account_name')
            account_number = request.POST.get('account_number')
            
            # รับไฟล์เอกสาร
            id_card_copy = request.FILES.get('id_card_copy')
            bank_book_copy = request.FILES.get('bank_book_copy')
            commerce_doc = request.FILES.get('commerce_doc')

            if not store_name or not owner_name:
                messages.error(request, 'กรุณากรอกข้อมูลที่จำเป็นให้ครบถ้วน')
                return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')

            Entrepreneur.objects.create(
                user=request.user,
                store_name=store_name,
                owner_name=owner_name,
                email=email,
                phone=phone,
                tax_id=tax_id,
                shop_address=shop_address,
                bank_name=bank_name,
                account_name=account_name,
                account_number=account_number,
                id_card_copy=id_card_copy,
                bank_book_copy=bank_book_copy,
                commerce_doc=commerce_doc,
                verification_status='pending'  # ⭐ ระบุสถานะรอตรวจสอบชัดเจน
            )
            
            messages.success(request, 'สมัครเป็นผู้ประกอบการเรียบร้อยแล้ว โปรดรอการตรวจสอบจากเจ้าหน้าที่')
            return redirect('petjoy:entrepreneur-home')
            
        return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')

    # ========================================================
    # กรณีที่ 2: ยังไม่เป็นสมาชิก (Anonymous Flow) -> สมัคร User + ร้านค้าพร้อมกัน
    # ========================================================
    if request.method == 'POST':
        # ข้อมูล User
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        
        # ข้อมูลร้านค้า (เพิ่มส่วนนี้ให้ครบเหมือนด้านบน)
        email = request.POST.get('email')
        store_name = request.POST.get('store_name')
        owner_name = request.POST.get('owner_name')
        phone = request.POST.get('phone')
        tax_id = request.POST.get('tax_id')
        shop_address = request.POST.get('shop_address')
        
        # รับข้อมูลธนาคารและไฟล์ (ส่วนที่ของเดิมของคุณขาดไป)
        bank_name = request.POST.get('bank_name')
        account_name = request.POST.get('account_name')
        account_number = request.POST.get('account_number')
        id_card_copy = request.FILES.get('id_card_copy')
        bank_book_copy = request.FILES.get('bank_book_copy')
        commerce_doc = request.FILES.get('commerce_doc')

        # Validation เบื้องต้น
        if not username or not password or not email or not store_name or not owner_name:
            messages.error(request, 'กรุณากรอกข้อมูลให้ครบถ้วน')
            return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')

        if password2 is None or password != password2:
            messages.error(request, 'รหัสผ่านทั้งสองช่องต้องตรงกัน')
            return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')

        # เช็คชื่อซ้ำ
        if Entrepreneur.objects.filter(email__iexact=email).exists():
            messages.error(request, 'มีร้านค้าที่ใช้อีเมลนี้อยู่แล้ว')
            return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')

        from django.contrib.auth import get_user_model
        User = get_user_model()
        if User.objects.filter(username__iexact=username).exists():
            messages.error(request, 'มีชื่อผู้ใช้นี้ในระบบแล้ว')
            return render(request, 'petjoy/entrepreneur/entrepreneur_register.html')

        # 1. สร้าง User ใหม่
        new_user = User.objects.create_user(username=username, email=email, password=password)
        
        # 2. สร้าง Entrepreneur ผูกกับ User ใหม่ (พร้อมเอกสารครบถ้วน)
        Entrepreneur.objects.create(
            user=new_user,
            store_name=store_name,
            owner_name=owner_name,
            email=email,
            phone=phone or '',
            tax_id=tax_id,
            shop_address=shop_address,
            bank_name=bank_name,
            account_name=account_name,
            account_number=account_number,
            id_card_copy=id_card_copy,
            bank_book_copy=bank_book_copy,
            commerce_doc=commerce_doc,
            verification_status='pending' # ⭐ ระบุสถานะรอตรวจสอบชัดเจน
        )

        # Log in อัตโนมัติ แล้วพาไปหน้า Home ร้านค้า
        try:
            login(request, new_user)
            messages.success(request, 'สมัครสมาชิกและส่งคำขอเปิดร้านเรียบร้อยแล้ว โปรดรอการอนุมัติ')
            return redirect('petjoy:entrepreneur-home')
        except Exception:
            messages.success(request, 'สมัครเรียบร้อยแล้ว กรุณาเข้าสู่ระบบ')
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

@login_required
def update_order_status(request, order_id): # ชื่อฟังก์ชันอาจแตกต่างกันไปตามระบบของคุณ
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == "POST":
        new_status = request.POST.get('status')
        cancel_reason = request.POST.get('cancel_reason')
        
        # ป้องกันการคืนสต๊อกซ้ำ (ถ้ายกเลิกไปแล้วไม่ต้องคืนอีก)
        if new_status == 'cancelled' and order.status != 'cancelled':
            with transaction.atomic():
                # คืนสต๊อกสินค้า
                for item in order.items.all():
                    product = item.product
                    product.stock += item.quantity
                    product.save()
                
                # บันทึกสถานะและเหตุผล
                order.status = new_status
                order.cancel_reason = cancel_reason
                order.save()
                
                messages.success(request, "ยกเลิกคำสั่งซื้อและคืนสินค้าเข้าสต๊อกเรียบร้อยแล้ว")
        else:
            # อัปเดตสถานะปกติอื่นๆ
            order.status = new_status
            order.save()
            messages.success(request, "อัปเดตสถานะเรียบร้อยแล้ว")
            
        return redirect('petjoy:orders-detail', order_id=order.id)

# views.py

# ==========================================
# 🚨 ADMIN REPORT & CHAT SYSTEM
# ==========================================

@login_required
def admin_report_list(request):
    """หน้ารายการสินค้าที่ถูกรายงาน"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")
    
    # ดึงข้อมูลการรายงานทั้งหมด (เรียงจากใหม่สุด)
    from .models import ProductReport
    reports = ProductReport.objects.all().order_by('-created_at')
    
    return render(request, 'petjoy/admin/admin_report_list.html', {'reports': reports})

@login_required
def admin_delete_product_reported(request, product_id):
    # เช็คสิทธิ์แอดมิน
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")

    product = get_object_or_404(Product, id=product_id)
    product_name = product.name
    
    # ลบแค่สินค้าตัวนี้ (ร้านค้า และ สินค้าชิ้นอื่น ยังอยู่ครบ)
    product.delete()
    
    messages.success(request, f"ลบสินค้า '{product_name}' ออกจากระบบแล้ว")
    return redirect('petjoy:admin-report-list')

@login_required
def admin_start_chat(request, entrepreneur_id):
    """เริ่มแชทกับร้านค้า (กดจากปุ่ม 'ติดต่อร้านค้า' ในหน้ารายงาน)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")

    entrepreneur = get_object_or_404(Entrepreneur, id=entrepreneur_id)
    
    # แอดมินจะทำตัวเป็น 'Customer' ในตาราง ChatRoom เพื่อคุยกับร้านค้า
    room, created = ChatRoom.objects.get_or_create(
        customer=request.user,
        entrepreneur=entrepreneur
    )
    
    return redirect('petjoy:admin-chat-room', room_id=room.id)

@login_required
def admin_chat_list(request):
    """หน้ารายการแชททั้งหมดของแอดมิน"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")

    # ดึงห้องแชทที่แอดมิน (ในฐานะ customer) คุยกับร้านต่างๆ
    rooms = ChatRoom.objects.filter(customer=request.user).order_by('-id')
    
    # ดึงห้องแชทที่ลูกค้าทักหาแอดมิน
    customer_rooms = CustomerAdminChatRoom.objects.all().order_by('-created_at')
    
    # ✨ ส่ง customer_rooms ไปพร้อมกับ rooms
    return render(request, 'petjoy/admin/admin_chat_list.html', {
        'rooms': rooms,
        'customer_rooms': customer_rooms
    })

@login_required
def admin_chat_room(request, room_id):
    """หน้าห้องแชทของแอดมิน (หน้าตาเหมือน Admin Panel)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")

    room = get_object_or_404(ChatRoom, id=room_id, customer=request.user)

    if request.method == 'POST':
        message_text = request.POST.get('message', '').strip()
        if message_text:
            ChatMessage.objects.create(
                room=room,
                sender=request.user,
                message=message_text
            )
            return redirect('petjoy:admin-chat-room', room_id=room.id)

    messages_list = room.messages.all().order_by('id')
    
    return render(request, 'petjoy/admin/admin_chat_room.html', {
        'room': room,
        'messages': messages_list,
        'current_user': request.user
    })

@login_required
def admin_orders_list(request):
    """หน้ารายการคำสั่งซื้อรวม (Placeholder)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")
    
    orders = Order.objects.all().order_by('-created_at')
    return render(request, 'petjoy/admin/admin_orders_list.html', {'orders': orders})

class EntrepreneurProductDetailView(View):
    def get(self, request, pk):
        if not request.user.is_authenticated or not hasattr(request.user, 'entrepreneur'):
            return redirect('petjoy:login')

        product = get_object_or_404(Product, pk=pk, owner=request.user.entrepreneur)

        return render(request, "petjoy/entrepreneur/entrepreneur_product_detail.html", {
            "product": product,
            "entrepreneur": request.user.entrepreneur
        })
    
@login_required
def admin_cleanup_orphans(request):
    """ฟังก์ชันล้างบาง: ลบร้านค้าและสินค้าที่ไม่มีเจ้าของ (User หาย)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")
    
    # หา Entrepreneur ที่ field 'user' เป็น Null (คือเจ้าของบัญชีโดนลบไปแล้ว)
    orphaned_shops = Entrepreneur.objects.filter(user__isnull=True)
    count = orphaned_shops.count()
    
    # ลบร้านพวกนั้นทิ้ง (สินค้าที่ผูกกับร้านพวกนี้จะหายไปด้วยถ้าตั้ง Cascade ไว้ หรือต้องสั่งลบเอง)
    for shop in orphaned_shops:
        # ลบสินค้าของร้านนี้ก่อน
        Product.objects.filter(owner=shop).delete()
        # ลบร้าน
        shop.delete()
        
    messages.success(request, f"ล้างข้อมูลขยะเรียบร้อย! ลบร้านค้าที่ไม่มีเจ้าของไป {count} ร้าน")
    return redirect("petjoy:admin-dashboard")

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



# views.py

class ProductDeleteView(DeleteView):
    model = Product
    template_name = 'petjoy/products/product_confirm_delete.html'
    
    # ไม่ใช้ success_url แบบ static แล้ว เพราะเราจะใช้ get_success_url แทน
    # success_url = reverse_lazy('petjoy:product-list') 

    # ---------------------------------------------------------
    # 1. กำหนดให้เด้งไปหน้า "จัดการร้านค้า" หลังลบเสร็จ
    # ---------------------------------------------------------
    def get_success_url(self):
        from django.urls import reverse_lazy
        # ✅ เปลี่ยนตรงนี้: ให้กลับไปหน้า Dashboard ร้านค้า (จะได้ไม่เจอ 404)
        return reverse_lazy('petjoy:entrepreneur-home')

    # ---------------------------------------------------------
    # 2. ตรวจสอบสิทธิ์ก่อนอนุญาตให้ลบ
    # ---------------------------------------------------------
    def dispatch(self, request, *args, **kwargs):
        # A. ต้องล็อกอินและเป็นผู้ประกอบการ
        if not request.user.is_authenticated or not hasattr(request.user, 'entrepreneur'):
            messages.error(request, 'คุณต้องเป็นผู้ประกอบการและล็อกอินก่อนลบสินค้า')
            return redirect('petjoy:login')

        # B. สินค้านี้ต้องเป็นของร้านเราจริงๆ (ห้ามลบของคนอื่น)
        obj = self.get_object()
        if obj.owner is None or obj.owner.user_id != request.user.id:
            messages.error(request, 'คุณไม่มีสิทธิ์ลบสินค้านี้')
            return redirect('petjoy:product-list')

        return super().dispatch(request, *args, **kwargs)

    # ---------------------------------------------------------
    # 3. ส่งข้อมูลร้านค้าไปที่ Template (เพื่อให้เมนู Sidebar ไม่หาย)
    # ---------------------------------------------------------
    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['entrepreneur'] = self.request.user.entrepreneur
        return ctx

    # ---------------------------------------------------------
    # 4. เพิ่มข้อความแจ้งเตือน "ลบสำเร็จ"
    # ---------------------------------------------------------
    def form_valid(self, form):
        messages.success(self.request, "🗑️ ลบสินค้าเรียบร้อยแล้ว")
        return super().form_valid(form)




@login_required
def entrepreneur_profile_settings(request):
    entrepreneur = get_object_or_404(Entrepreneur, user=request.user)
    quick_replies = QuickReply.objects.filter(entrepreneur=entrepreneur).order_by('-created_at')

    if request.method == 'POST':
        
        # --- 1. บันทึกข้อมูลภาษี (Tax ID) ---
        if 'save_tax' in request.POST:
            entrepreneur.tax_id = request.POST.get('tax_id')
            entrepreneur.save()
            messages.success(request, "บันทึกข้อมูลภาษีเรียบร้อยแล้ว")
            return redirect('petjoy:entrepreneur_profile_settings')

        # --- 2. บันทึกที่อยู่ร้าน ---
        elif 'save_address' in request.POST:
            entrepreneur.shop_address = request.POST.get('shop_address')
            entrepreneur.save()
            messages.success(request, "บันทึกที่อยู่เรียบร้อยแล้ว")
            return redirect('petjoy:entrepreneur_profile_settings')

        # --- 3. บันทึกบัญชีธนาคาร ---
        elif 'save_bank' in request.POST:
            entrepreneur.bank_name = request.POST.get('bank_name')
            entrepreneur.account_name = request.POST.get('account_name')
            entrepreneur.account_number = request.POST.get('account_number')
            
            if request.FILES.get('bank_book_copy'):
                entrepreneur.bank_book_copy = request.FILES['bank_book_copy']
                
            entrepreneur.save()
            messages.success(request, "บันทึกข้อมูลบัญชีธนาคารเรียบร้อยแล้ว")
            return redirect('petjoy:entrepreneur_profile_settings')

        # --- 4. บันทึกเอกสารยืนยันตัวตน ---
        elif 'save_idcard' in request.POST:
            if request.FILES.get('id_card_copy'):
                entrepreneur.id_card_copy = request.FILES['id_card_copy']
                entrepreneur.save()
                messages.success(request, "บันทึกเอกสารยืนยันตัวตนเรียบร้อยแล้ว")
            return redirect('petjoy:entrepreneur_profile_settings')

        # --- 5. เพิ่มข้อความด่วน ---
        elif 'add_quick_reply' in request.POST:
            message_text = request.POST.get('quick_message')
            if message_text:
                QuickReply.objects.create(entrepreneur=entrepreneur, message=message_text)
                messages.success(request, "เพิ่มข้อความด่วนเรียบร้อยแล้ว")
            return redirect('petjoy:entrepreneur_profile_settings')

        # --- 6. ลบข้อความด่วน ---
        elif 'delete_quick_reply' in request.POST:
            reply_id = request.POST.get('reply_id')
            QuickReply.objects.filter(id=reply_id, entrepreneur=entrepreneur).delete()
            messages.success(request, "ลบข้อความเรียบร้อยแล้ว")
            return redirect('petjoy:entrepreneur_profile_settings')

        # --- ⭐ 7. (ใหม่) บันทึกค่าจัดส่ง ---
        elif 'save_shipping' in request.POST:
            cost = request.POST.get('shipping_cost')
            try:
                # แปลงเป็น float, ถ้าว่างให้เป็น 0
                entrepreneur.shipping_cost = float(cost) if cost else 0.00
            except ValueError:
                entrepreneur.shipping_cost = 0.00
            
            entrepreneur.save()
            messages.success(request, "บันทึกค่าจัดส่งเรียบร้อยแล้ว")
            return redirect('petjoy:entrepreneur_profile_settings')

    return render(request, 'petjoy/entrepreneur/entrepreneur_profile_settings.html', {
        'entrepreneur': entrepreneur,
        'quick_replies': quick_replies,
    })

@login_required(login_url=reverse_lazy('petjoy:login'))
def entrepreneur_reviews(request):
    # ป้องกัน user ทั่วไป
    if not hasattr(request.user, 'entrepreneur'):
        messages.error(request, "คุณต้องเป็นผู้ประกอบการก่อน")
        return redirect('petjoy:login')

    entrepreneur = request.user.entrepreneur

    # =========================
    # 📝 ส่วนบันทึกคำตอบ (POST) - เพิ่มส่วนนี้เข้าไป
    # =========================
    if request.method == "POST":
        review_id = request.POST.get('review_id')
        reply_text = request.POST.get('message')
        
        try:
            target_review = Review.objects.get(id=review_id)
            
            # บันทึกหรืออัปเดตการตอบกลับ
            ReviewReply.objects.update_or_create(
                review=target_review,
                defaults={'message': reply_text}
            )
            
            # เปิดการแจ้งเตือนให้ลูกค้าผ่าน Model Order
            if target_review.order:
                order_to_notify = target_review.order
                order_to_notify.has_unread_status_update = True
                order_to_notify.save()
            
            messages.success(request, "ส่งการตอบกลับเรียบร้อยแล้ว")
            
        except Review.DoesNotExist:
            messages.error(request, "ไม่พบรีวิวที่ต้องการตอบกลับ")
        except Exception as e:
            messages.error(request, f"เกิดข้อผิดพลาด: {str(e)}")
            
        # รีโหลดหน้าเดิมเพื่อแสดงผลลัพธ์
        return redirect('petjoy:entrepreneur_reviews')

    # =========================
    # 🔍 ส่วนดึงข้อมูล (GET) - ของเดิมของคุณ
    # =========================
    
    # Base Queryset
    reviews = Review.objects.filter(
        product__owner=entrepreneur  # แก้ตรงนี้ให้ตรงกับ Model Product ของคุณ (บางทีอาจใช้ entrepreneur=entrepreneur)
    ).select_related(
        'product',
        'user'
    ).prefetch_related(
        'reply'
    )

    # Filter Logic
    filter_type = request.GET.get('filter', 'all')

    if filter_type == 'unreplied':
        reviews = reviews.filter(reply__isnull=True).order_by('-created_at')
    elif filter_type == 'replied_latest':
        reviews = reviews.filter(reply__isnull=False).order_by('-reply__created_at')
    else:
        reviews = reviews.order_by('-created_at')

    return render(request, 'petjoy/entrepreneur/reviews.html', {
        'entrepreneur': entrepreneur,
        'reviews': reviews,
        'current_filter': filter_type,
    })


from django.db.models import Sum

@login_required(login_url=reverse_lazy('petjoy:login'))
def entrepreneur_home(request):
    from .models import Product, Review, Order, Entrepreneur # ตรวจสอบการ import

    try:
        entrepreneur = request.user.entrepreneur
    except Exception:
        messages.info(request, 'กรุณาสมัครเป็นผู้ประกอบการก่อนเข้าหน้านี้')
        return redirect('petjoy:entrepreneur-register')

    # ⭐ ส่วนที่เพิ่ม: ดักจับสถานะการอนุมัติ ⭐
    if entrepreneur.verification_status == 'pending':
        # ถ้ายังรอการตรวจสอบ ให้แสดงหน้า "รออนุมัติ"
        return render(request, 'petjoy/entrepreneur/entrepreneur_waiting.html', {'entrepreneur': entrepreneur})
    
    elif entrepreneur.verification_status == 'rejected':
        # ถ้าถูกปฏิเสธ ให้แสดงหน้า "ถูกปฏิเสธ"
        return render(request, 'petjoy/entrepreneur/entrepreneur_rejected.html', {'entrepreneur': entrepreneur})

    # --- กรณีได้รับอนุมัติแล้ว (approved) ให้ทำงานตามปกติด้านล่าง ---
    products = Product.objects.filter(owner=entrepreneur)
    product_count = products.count()

    # ⭐ คะแนนเฉลี่ย
    all_reviews = Review.objects.filter(product__in=products)
    avg_score = (
        round(all_reviews.aggregate(Avg('rating'))['rating__avg'], 2)
        if all_reviews.exists()
        else None
    )

    # ⭐⭐ ยอดขายสะสม ⭐⭐
    income_statuses = ["paid", "preparing", "delivering", "success"]
    total_sales = (
        Order.objects.filter(
            entrepreneur=entrepreneur,
            status__in=income_statuses
        ).aggregate(total=Sum("total_price"))["total"] or 0
    )

    return render(request, 'petjoy/entrepreneur/entrepreneur_home.html', {
        'product_count': product_count,
        'products': products,
        'avg_score': avg_score,
        'entrepreneur': entrepreneur,
        'total_sales': total_sales,
    })

@login_required
def admin_dashboard(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")

    from django.contrib.auth import get_user_model
    from .models import Entrepreneur, Order, ProductReport 
    from django.db.models import Sum

    User = get_user_model()

    # --- 1. ข้อมูลสรุปบนการ์ด (นับสดๆ จาก DB) ---
    # นับเฉพาะ User ทั่วไป (ไม่รวม Admin และ ร้านค้า)
    total_general_users = User.objects.filter(is_superuser=False, entrepreneur__isnull=True).count()
    
    # ⭐ แก้ไข: ร้านค้าที่อนุมัติแล้ว (ไม่นับร้านของแอดมิน)
    total_shops = Entrepreneur.objects.exclude(user__is_superuser=True).filter(verification_status='approved').count()
    
    # ⭐ แก้ไข: ร้านค้าที่รออนุมัติ (ไม่นับร้านของแอดมิน)
    pending_shops_count = Entrepreneur.objects.exclude(user__is_superuser=True).filter(verification_status='pending').count()
    
    # รายได้รวม (เฉพาะออเดอร์ที่สำเร็จ + ร้านต้อง Active อยู่)
    total_income = Order.objects.filter(
        status__in=["paid", "preparing", "delivering", "success"], # สถานะออเดอร์ปกติ
        entrepreneur__isnull=False,                   # ร้านต้องมีอยู่จริง
        entrepreneur__verification_status='approved', # ร้านต้องอนุมัติแล้ว
        entrepreneur__user__isnull=False,             # User เจ้าของต้องไม่ถูกลบ
        entrepreneur__user__profile__is_banned=False  # User ต้องไม่โดนแบน
    ).aggregate(total=Sum("total_price"))["total"] or 0

    # --- 2. ดึงรายงานล่าสุด 10 รายการ ---
    # ใช้ select_related เพื่อลด Query และดึงข้อมูล User/Product ทันที
    recent_reports = ProductReport.objects.select_related('product', 'product__owner', 'user').order_by('-created_at')[:10]

    # --- 3. ⭐ แก้ไข: ร้านค้าล่าสุด (ไม่ดึงร้านของแอดมินมาโชว์ในตาราง) ---
    recent_shops = Entrepreneur.objects.exclude(user__is_superuser=True).filter(verification_status='approved').order_by("-id")[:5]

    context = {
        "total_users": total_general_users, 
        "total_shops": total_shops,
        "pending_shops": pending_shops_count,
        "total_income": total_income,
        "recent_reports": recent_reports,
        "recent_shops": recent_shops,
    }

    return render(request, "petjoy/admin/admin_dashboard.html", context)

@login_required
def admin_user_list(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")

    User = get_user_model()
    
    # รับค่าจาก Parameter
    search = request.GET.get("q", "")
    user_type = request.GET.get("type", "")

    users = User.objects.all().order_by('-date_joined') # เรียงตามสมัครล่าสุด

    # --- ส่วนที่เพิ่ม: Logic สำหรับ Filter ---
    if user_type == 'admin':
        users = users.filter(is_superuser=True)
    elif user_type == 'entrepreneur':
        # ✅ แก้ตรงนี้: กรองคนที่มีข้อมูลในตาราง Entrepreneur "และต้องไม่ใช่แอดมิน"
        users = users.filter(entrepreneur__isnull=False, is_superuser=False)
    elif user_type == 'user':
        # กรองคนที่ไม่ใช่ admin และไม่ใช่ entrepreneur
        users = users.filter(is_superuser=False, entrepreneur__isnull=True)
    # ------------------------------------

    # Logic สำหรับค้นหา (เดิม)
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(email__icontains=search)
        )

    context = {
        "users": users,
        "search": search,
        "current_type": user_type, # ส่งค่ากลับไปเพื่อให้ Dropdown เลือกค่าเดิมไว้
    }

    return render(request, "petjoy/admin/admin_users.html", context)

@login_required
def admin_user_detail(request, user_id):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")

    User = get_user_model()
    user = get_object_or_404(User, id=user_id)

    # ดึง Profile แบบปลอดภัย (กัน Error)
    profile = None
    if hasattr(user, 'profile'):
        profile = user.profile

    entrepreneur = None
    if hasattr(user, "entrepreneur"):
        entrepreneur = user.entrepreneur

    context = {
        "profile_user": user,
        "user_profile": profile, # ⭐ ส่งตัวนี้ไปใช้ใน HTML แทน
        "entrepreneur": entrepreneur,
    }

    return render(request, "petjoy/admin/admin_user_detail.html", context)

@login_required
def admin_toggle_ban(request, user_id):
    # เช็คสิทธิ์แอดมิน
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")

    User = get_user_model()
    target_user = get_object_or_404(User, id=user_id)
    
    # สร้าง Profile หากยังไม่มี
    profile, created = Profile.objects.get_or_create(user=target_user)

    # ป้องกันแบนตัวเอง
    if target_user.id == request.user.id:
        messages.error(request, "ไม่สามารถระงับบัญชีของตนเองได้")
        return redirect(request.META.get('HTTP_REFERER', 'petjoy:admin-users'))

    # สลับสถานะ Ban
    profile.is_banned = not profile.is_banned
    profile.save()

    # ⭐ แก้ไข: บังคับให้ User Active เสมอ (เพื่อให้ล็อกอินเข้ามาเจอหน้าแจ้งเตือนได้) ⭐
    if not target_user.is_active:
        target_user.is_active = True
        target_user.save()

    if profile.is_banned:
        # ถ้าระงับ -> เตะออกจากระบบทันที (เผื่อเขาออนไลน์อยู่)
        from django.contrib.sessions.models import Session
        # (โค้ดส่วนนี้อาจจะซับซ้อนไป ให้ระบบ Middleware จัดการดีดออกเองตอนเขากดเปลี่ยนหน้าก็ได้ครับ)
        messages.warning(request, f"ระงับบัญชี {target_user.username} เรียบร้อยแล้ว")
    else:
        messages.success(request, f"ปลดการระงับบัญชี {target_user.username} เรียบร้อยแล้ว")

    return redirect(request.META.get('HTTP_REFERER', 'petjoy:admin-users'))



@login_required
def admin_delete_user(request, user_id):
    # เช็คสิทธิ์แอดมิน
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")

    User = get_user_model()
    target_user = get_object_or_404(User, id=user_id)

    # ป้องกันลบตัวเอง
    if target_user == request.user:
        messages.error(request, "ไม่สามารถลบบัญชีของตนเองได้")
        return redirect("petjoy:admin-users")

    username = target_user.username

    try:
        with transaction.atomic():
            # ถ้าเป็นร้านค้า -> ลบสินค้าและข้อมูลร้านทิ้งทั้งหมด (แก้ปัญหา SET_NULL ที่ทำให้สินค้าค้าง)
            if hasattr(target_user, 'entrepreneur'):
                shop = target_user.entrepreneur
                
                # 1. ลบสินค้าทั้งหมดของร้านนี้
                Product.objects.filter(owner=shop).delete()
                
                # 2. ลบห้องแชทของร้านนี้
                ChatRoom.objects.filter(entrepreneur=shop).delete()
                
                # 3. ลบข้อมูลร้านค้า
                shop.delete()

            # 4. ลบโปรไฟล์ (ถ้ามี)
            if hasattr(target_user, 'profile'):
                target_user.profile.delete()

            # 5. สุดท้ายลบ User
            target_user.delete()

        messages.success(request, f"ลบบัญชี {username} และข้อมูลร้านค้า/สินค้าทั้งหมด เรียบร้อยแล้ว")
        
    except Exception as e:
        messages.error(request, f"เกิดข้อผิดพลาด: {str(e)}")

    return redirect("petjoy:admin-users")


@login_required
def admin_shop_list(request):
    """หน้ารายการคำขอเปิดร้านค้า"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")

    status_filter = request.GET.get('status', '') # รับค่า filter
    search_query = request.GET.get('q', '')

    shops = Entrepreneur.objects.exclude(user__is_staff=True).order_by('-id')

    # Filter ตามสถานะ
    if status_filter:
        shops = shops.filter(verification_status=status_filter)

    # Search
    if search_query:
        shops = shops.filter(
            Q(store_name__icontains=search_query) |
            Q(owner_name__icontains=search_query) |
            Q(email__icontains=search_query)
        )

    context = {
        'shops': shops,
        'current_status': status_filter,
        'search': search_query
    }
    return render(request, 'petjoy/admin/admin_shop_list.html', context)

@login_required
def admin_shop_detail(request, pk):
    """หน้าดูรายละเอียดร้านค้าเพื่อพิจารณา"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")

    shop = get_object_or_404(Entrepreneur, pk=pk)
    return render(request, 'petjoy/admin/admin_shop_detail.html', {'shop': shop})

@login_required
def admin_approve_shop(request, pk):
    """ฟังก์ชันกดอนุมัติ"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")
        
    shop = get_object_or_404(Entrepreneur, pk=pk)
    shop.verification_status = 'approved'
    shop.save()
    
    messages.success(request, f"อนุมัติร้าน {shop.store_name} เรียบร้อยแล้ว")
    return redirect('petjoy:admin-shop-detail', pk=pk)

@login_required
def admin_reject_shop(request, pk):
    """ฟังก์ชันกดปฏิเสธ"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")
        
    shop = get_object_or_404(Entrepreneur, pk=pk)
    shop.verification_status = 'rejected'
    shop.save()
    
    messages.error(request, f"ปฏิเสธคำขอร้าน {shop.store_name} แล้ว")
    return redirect('petjoy:admin-shop-detail', pk=pk)



@login_required
def admin_start_chat_from_report(request, report_id):
    """
    เริ่มแชทกับร้านค้าจากหน้ารายงานปัญหา พร้อมส่งข้อความเตือนอัตโนมัติ
    """
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")

    # ⭐ เพิ่มบรรทัดนี้เพื่อแก้ NameError ครับ ⭐
    from .models import ProductReport, ChatRoom, ChatMessage

    # ดึงข้อมูลรายงาน
    report = get_object_or_404(ProductReport, id=report_id)
    entrepreneur = report.product.owner
    
    # สร้างหรือดึงห้องแชท
    room, created = ChatRoom.objects.get_or_create(
        customer=request.user,
        entrepreneur=entrepreneur
    )
    
    # ข้อความแจ้งเตือนอัตโนมัติ
    warning_message = (
        f"⚠️ แจ้งเตือนจากแอดมิน: สินค้าของคุณ '{report.product.name}' ถูกรายงาน\n"
        f"หัวข้อ: {report.get_reason_display()}\n"
        f"รายละเอียด: {report.details or '-'}\n"
        f"กรุณาตรวจสอบความถูกต้องหรือแก้ไขสินค้า หากพบการละเมิดจะถูกลบออกจากระบบ"
    )

    # ตรวจสอบเพื่อไม่ให้ส่งข้อความซ้ำ (ถ้าข้อความล่าสุดเหมือนกันเป๊ะจะไม่ส่ง)
    last_msg = room.messages.last()
    if not last_msg or last_msg.message != warning_message:
        ChatMessage.objects.create(
            room=room,
            sender=request.user,
            message=warning_message
        )
    
    # ส่งไปที่ห้องแชท
    return redirect('petjoy:admin-chat-room', room_id=room.id)

@login_required
def admin_delete_chat(request, room_id):
    # เช็คสิทธิ์แอดมิน
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")
    
    room = get_object_or_404(ChatRoom, id=room_id)
    
    # ลบแค่ห้องแชท (User และ ร้านค้า ไม่ได้รับผลกระทบ)
    room.delete()
    
    messages.success(request, "ลบประวัติการสนทนาเรียบร้อยแล้ว")
    return redirect('petjoy:admin-chat-list')


@login_required
def admin_product_detail(request, product_id):
    """หน้าดูรายละเอียดสินค้าฉบับแอดมิน (เห็นข้อมูล + รายงาน)"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect("petjoy:homepage")
    
    product = get_object_or_404(Product, id=product_id)
    # ดึงรายงานทั้งหมดของสินค้านี้มาแสดงด้วย
    reports = product.reports.all().order_by('-created_at')

    return render(request, 'petjoy/admin/admin_product_detail.html', {
        'product': product,
        'reports': reports
    })

@staff_member_required
def admin_delete_report(request, report_id):
    report = get_object_or_404(ProductReport, id=report_id)
    report.delete()
    messages.success(request, "ลบรายงานเรียบร้อยแล้ว")
    return redirect('petjoy:admin-report-list')


@staff_member_required
def admin_order_analytics(request):
    # --- 1. สรุปภาพรวม ---
    valid_statuses = ['paid', 'preparing', 'delivering', 'success']
    orders = Order.objects.filter(
        status__in=valid_statuses,
        entrepreneur__isnull=False,
        entrepreneur__verification_status='approved',
        entrepreneur__user__isnull=False,
        entrepreneur__user__profile__is_banned=False
    )

    total_revenue = orders.aggregate(total=Sum('total_price'))['total'] or 0
    total_orders_count = orders.count()
    
    # นับร้านค้าที่อนุมัติแล้ว
    total_shops = Entrepreneur.objects.filter(verification_status='approved').count()

    # --- 2.1 5 อันดับสินค้าขายดี (เฉพาะจากร้านที่อนุมัติแล้ว) ---
    # ✨ เพิ่ม 'product__owner__store_name' เข้ามาดึงชื่อร้าน
    top_products_query = OrderItem.objects.filter(
        order__in=orders,
        product__owner__verification_status='approved'  
    ).values('product__name', 'product__owner__store_name') \
     .annotate(total_sold=Sum('quantity')) \
     .order_by('-total_sold')[:5]
    
    # ✨ เปลี่ยนตรงนี้: เอาชื่อสินค้า + ชื่อร้านค้า มารวมกันเป็น Label ของกราฟ
    top_products_labels = [
        f"{item['product__name']} (ร้าน: {item['product__owner__store_name'] or 'ไม่ระบุ'})" 
        for item in top_products_query
    ]
    top_products_data = [item['total_sold'] for item in top_products_query]

    # --- 2.2 5 อันดับร้านค้าขายดี (เฉพาะร้านที่อนุมัติแล้ว) ---
    top_shops_query = OrderItem.objects.filter(
        order__in=orders,
        product__owner__verification_status='approved'  
    ).values('product__owner__store_name') \
     .annotate(total_sold=Sum('quantity')) \
     .order_by('-total_sold')[:5]
    
    top_shops_labels = [item['product__owner__store_name'] or 'ไม่ระบุชื่อร้าน' for item in top_shops_query]
    top_shops_data = [item['total_sold'] for item in top_shops_query]

    # --- 3. หมวดหมู่ยอดนิยม ---
    category_sales = OrderItem.objects.filter(order__in=orders) \
        .values('product__category__display_name') \
        .annotate(total_sold=Sum('quantity')) \
        .order_by('-total_sold')
    
    category_labels = [item['product__category__display_name'] for item in category_sales]
    category_data = [item['total_sold'] for item in category_sales]

    # ข้อมูลแยกประเภทอาหาร
    food_type_sales = OrderItem.objects.filter(order__in=orders, product__category__name='food') \
        .values('product__food_type') \
        .annotate(total_sold=Sum('quantity'))
    
    food_type_labels = []
    food_type_data = []
    for item in food_type_sales:
        label = "อาหารสุนัข" if item['product__food_type'] == 'dog' else "อาหารแมว" if item['product__food_type'] == 'cat' else "อื่นๆ"
        food_type_labels.append(label)
        food_type_data.append(item['total_sold'])

    # --- 4. สถิติรายได้ย้อนหลัง 7 วัน ---
    last_7_days = []
    revenue_data = []
    for i in range(6, -1, -1):
        date = timezone.now().date() - timedelta(days=i)
        daily_revenue = orders.filter(created_at__date=date).aggregate(total=Sum('total_price'))['total'] or 0
        last_7_days.append(date.strftime('%d %b'))
        revenue_data.append(float(daily_revenue))

    context = {
        'total_revenue': total_revenue,
        'total_orders_count': total_orders_count,
        'total_shops': total_shops,
        
        # ✅ แปลงเป็น JSON String ทั้งหมด แก้ปัญหากราฟไม่ขึ้น
        'top_products_labels': json.dumps(top_products_labels),
        'top_products_data': json.dumps(top_products_data),
        'top_shops_labels': json.dumps(top_shops_labels),
        'top_shops_data': json.dumps(top_shops_data),
        'category_labels': json.dumps(category_labels),
        'category_data': json.dumps(category_data),
        'food_type_labels': json.dumps(food_type_labels),
        'food_type_data': json.dumps(food_type_data),
        'revenue_labels': json.dumps(last_7_days),
        'revenue_data': json.dumps(revenue_data),
    }
    return render(request, 'petjoy/admin/admin_orders_analytics.html', context)

@staff_member_required
def admin_category_settings(request):
    categories = Category.objects.all().order_by('id')

    if request.method == "POST":
        action = request.POST.get("action")

        # =====================
        # เพิ่มหมวดหมู่
        # =====================
        if action == "add":
            name = request.POST.get("name")
            display_name = request.POST.get("display_name")
            image = request.FILES.get("image")

            if name and display_name:
                Category.objects.create(
                    name=name.strip().lower(),
                    display_name=display_name.strip(),
                    image=image
                )

        # =====================
        # แก้ไขหมวดหมู่ (ชื่อ / รูป)
        # =====================
        elif action == "edit":
            cat_id = request.POST.get("id")
            display_name = request.POST.get("display_name")
            image = request.FILES.get("image")

            category = get_object_or_404(Category, id=cat_id)

            if display_name:
                category.display_name = display_name.strip()

            # ถ้าอัปโหลดรูปใหม่ → แทนรูปเดิม
            if image:
                category.image = image

            category.save()

        # =====================
        # ลบหมวดหมู่
        # =====================
        elif action == "delete":
            cat_id = request.POST.get("id")
            if cat_id:
                Category.objects.filter(id=cat_id).delete()

        return redirect("petjoy:admin-category-settings")

    return render(
        request,
        "petjoy/admin/admin_category_settings.html",
        {
            "categories": categories
        }
    )

def banned_view(request):
    """แสดงหน้าแจ้งเตือนเมื่อบัญชีถูกระงับ"""
    return render(request, 'petjoy/banned.html')

def login_view(request):
    next_url = request.GET.get('next') or request.POST.get('next')

    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # 1. ลอง Login แบบปกติ
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.info(request, f"ยินดีต้อนรับ, {username}!")
                
                # ⭐ พอ Login ผ่าน Middleware จะทำงานอัตโนมัติ 
                # ถ้าโดนแบนอยู่ จะถูกดีดไปหน้า banned เองทันที

                if next_url: return redirect(next_url)
                if user.is_staff or user.is_superuser: return redirect("petjoy:admin-dashboard")
                if hasattr(user, 'entrepreneur') or hasattr(user, 'entrepreneur_profile'): return redirect("petjoy:entrepreneur-home")
                return redirect("petjoy:homepage")

            else:
                # 2. Fallback: กรณีพิมพ์ User ผิด Case (ตัวเล็ก/ใหญ่)
                User = get_user_model()
                target_user = User.objects.filter(username__iexact=username).first()

                if target_user and target_user.check_password(password):
                    # Login ใหม่อีกรอบด้วยชื่อที่ถูกต้อง
                    user = authenticate(username=target_user.username, password=password)
                    
                    if user is not None:
                        login(request, user)
                        messages.info(request, f"ยินดีต้อนรับ, {target_user.username}!")
                        
                        # Redirect Logic (เหมือนด้านบน)
                        if next_url: return redirect(next_url)
                        if user.is_staff or user.is_superuser: return redirect("petjoy:admin-dashboard")
                        if hasattr(user, 'entrepreneur') or hasattr(user, 'entrepreneur_profile'): return redirect("petjoy:entrepreneur-home")
                        return redirect("petjoy:homepage")
                    else:
                         messages.error(request, "เกิดข้อผิดพลาดในการเข้าสู่ระบบ")
                else:
                    messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

        else:
            messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    else:
        form = AuthenticationForm(request)

    return render(
        request,
        "petjoy/login.html",
        context={"login_form": form, "auth_page": True, "next": next_url}
    )

def category_products(request, category_id):
    category = get_object_or_404(Category, id=category_id)

    # ⭐ แสดงเฉพาะสินค้าของร้านที่ "อนุมัติแล้ว"
    products = Product.objects.filter(
        category=category,
        owner__verification_status='approved'
    )

    # 🔹 กรณีหมวดอาหาร แยก dog / cat
    selected_type = request.GET.get("type")
    if "อาหาร" in category.display_name and selected_type in ["dog", "cat"]:
        products = products.filter(food_type=selected_type)

    # 🔹 pagination
    paginator = Paginator(products, 15)  # 15 สินค้าต่อหน้า
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "petjoy/category_products.html", {
        "category": category,
        "products": page_obj,
        "page_obj": page_obj,
        "selected_type": selected_type
    })

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
def entrepreneur_income(request):
    entrepreneur = request.user.entrepreneur

    range_days = request.GET.get("range", "all")

    income_statuses = ["paid", "preparing", "delivering", "success"]

    qs = Order.objects.filter(
        entrepreneur=entrepreneur,
        status__in=income_statuses
    )

    if range_days != "all":
        days = int(range_days)
        start_date = timezone.now() - timedelta(days=days)
        qs = qs.filter(created_at__gte=start_date)

    daily = (
        qs.annotate(day=TruncDate("created_at"))
          .values("day")
          .annotate(total=Sum("total_price"))
          .order_by("day")
    )

    labels = [x["day"].strftime("%Y-%m-%d") for x in daily]
    values = [float(x["total"] or 0) for x in daily]

    total_income = qs.aggregate(total=Sum("total_price"))["total"] or 0
    total_orders = qs.count()
    avg_income = total_income / len(values) if values else 0

    context = {
        "entrepreneur": entrepreneur,
        "labels_json": json.dumps(labels),
        "values_json": json.dumps(values),
        "total_income": total_income,
        "total_orders": total_orders,
        "avg_income": avg_income,
        "range": range_days,
    }

    return render(
        request,
        "petjoy/entrepreneur/entrepreneur_income.html",
        context
    )


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


def search_view(request):
    # รับคำค้นหา
    q = request.GET.get('q', '').strip()
    
    # เริ่มต้นด้วย QuerySet ว่างๆ
    products = Product.objects.none()
    categories = Category.objects.none()
    
    if q:
        # 1. ค้นหาจากชื่อ, รายละเอียด, คุณสมบัติ
        products = Product.objects.filter(
            Q(name__icontains=q) | 
            Q(description__icontains=q) | 
            Q(features__icontains=q)
        )

        # ⭐⭐ 2. เพิ่มส่วนกรอง: เอาเฉพาะร้านที่ Active จริงๆ เท่านั้น ⭐⭐
        # (ป้องกันสินค้าจากร้านที่ถูกลบ หรือร้านผีโผล่ขึ้นมา)
        products = products.filter(
            owner__isnull=False,                        # สินค้าต้องมีเจ้าของ (ร้านค้า)
            owner__verification_status='approved',      # ร้านต้องได้รับการอนุมัติแล้ว
            owner__user__isnull=False,                  # User เจ้าของร้านต้องไม่ถูกลบ
            owner__user__profile__is_banned=False       # User เจ้าของร้านต้องไม่โดนแบน
        )

        # 3. ค้นหาหมวดหมู่ (เผื่อลูกค้าค้นหาชื่อหมวดหมู่)
        categories = Category.objects.filter(
            Q(name__icontains=q) | 
            Q(display_name__icontains=q)
        )

    return render(request, 'petjoy/search_results.html', {
        'query': q,
        'products': products,
        'categories': categories,
    })

@login_required
def start_chat_admin(request):
    """
    สร้างหรือดึงห้องแชทระหว่าง User (ลูกค้า) กับ Admin (Superuser)
    """
    # 1. หา Admin สักคนในระบบ (ดึงคนแรกที่เป็น superuser)
    admin_user = get_user_model().objects.filter(is_superuser=True).first()
    
    if not admin_user:
        messages.error(request, "ไม่พบข้อมูลผู้ดูแลระบบในขณะนี้")
        return redirect('petjoy:chat_list')

    # 2. ตรวจสอบว่ามีห้องแชทระหว่าง ลูกค้า(customer) และ Admin นี้อยู่แล้วหรือยัง
    # โดยอิงจาก customer=request.user และ entrepreneur=None (หรือถ้า ChatRoom คุณเชื่อม User กับ User ให้เช็คแบบนั้น)
    # **หมายเหตุ:** โครงสร้าง ChatRoom ของคุณปกติเชื่อม Customer กับ Entrepreneur
    # หากแอดมินไม่มี Entrepreneur profile เราจะประยุกต์ใช้ field อื่น หรือสร้าง dummy
    
    # สมมติว่าในระบบของคุณ ChatRoom เชื่อมผ่าน `customer` และ `entrepreneur`
    # วิธีที่ง่ายที่สุดสำหรับโครงสร้างเดิมคือการหา/สร้าง Entrepreneur ที่เป็นของ Admin
    admin_entrepreneur, created = Entrepreneur.objects.get_or_create(
        user=admin_user,
        defaults={
            'store_name': 'Admin Support',
            'phone': '0000000000',
            'verification_status': 'approved'
        }
    )

    room, created = ChatRoom.objects.get_or_create(
        customer=request.user,
        entrepreneur=admin_entrepreneur
    )

    # 3. ส่งลูกค้าเข้าไปในห้องแชทที่ได้
    return redirect('petjoy:chat_room', room_id=room.id)


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
        "canceled_count": orders.filter(status="cancelled").count(),

        # - 5 orders ล่าสุด
        "recent_orders": orders[:5],
    }

    return render(request, "petjoy/entrepreneur/orders_list.html", context)

@login_required
def order_detail(request, order_id): 
    # ดึงข้อมูลออเดอร์ของร้านนี้
    entrepreneur = request.user.entrepreneur
    order = get_object_or_404(Order, id=order_id, entrepreneur=entrepreneur)

    if request.method == "POST":
        
        # 🟢 1. ส่วนรับคำสั่งจากปุ่ม "อนุมัติ" หรือ "ปฏิเสธ" คำร้องขอยกเลิก
        action = request.POST.get("action")
        
        if action == "approve_cancel":
            if order.status == "cancel_requested":
                # อนุมัติ -> เปลี่ยนสถานะเป็นยกเลิก และคืนสต๊อก
                order.status = "cancelled"
                order.cancel_reason = "ร้านค้าอนุมัติการยกเลิกแล้ว"
                order.has_unread_status_update = True
                order.save()
                
                for item in order.items.all():
                    item.product.stock += item.quantity
                    item.product.save()
                    
                messages.success(request, "อนุมัติการยกเลิกคำสั่งซื้อเรียบร้อยแล้ว")
                return redirect("petjoy:orders-detail", order_id=order.id)
                
        elif action == "reject_cancel":
            if order.status == "cancel_requested":
                # ปฏิเสธ -> คืนสถานะกลับเป็น "กำลังเตรียมของ"
                order.status = "preparing" 
                order.has_unread_status_update = True
                order.save()
                
                messages.error(request, "ปฏิเสธคำร้องขอยกเลิก ระบบแจ้งเตือนลูกค้าแล้ว")
                return redirect("petjoy:orders-detail", order_id=order.id)

        # 🟢 2. โค้ดเดิมของคุณ (สำหรับเปลี่ยนสถานะออเดอร์ปกติ)
        new_status = request.POST.get("status")
        if new_status: # ใส่ if ครอบไว้กันชนกับข้างบน
            tracking_number = request.POST.get("tracking_number")
            cancel_reason = request.POST.get("cancel_reason")

            # เงื่อนไขคืนสต๊อกตรงนี้ (ของคุณเดิม)
            if new_status == 'cancelled' and order.status != 'cancelled':
                for item in order.items.all():
                    item.product.stock += item.quantity
                    item.product.save()

            # อัปเดตข้อมูลออเดอร์
            order.status = new_status
            if new_status == 'delivering':
                order.tracking_number = tracking_number
            if new_status == 'cancelled':
                order.cancel_reason = cancel_reason

            order.has_unread_status_update = True
            order.save()
            
            messages.success(request, "อัปเดตสถานะคำสั่งซื้อเรียบร้อยแล้ว")
            return redirect("petjoy:orders-detail", order_id=order.id)
    
    return render(request, "petjoy/entrepreneur/orders_detail.html", {
        "order": order,
        "entrepreneur": entrepreneur
    })

@login_required
def cancel_order(request, order_id):
    entrepreneur = request.user.entrepreneur
    order = get_object_or_404(Order, id=order_id, entrepreneur=entrepreneur)

    if order.status in ['paid', 'preparing']:
        order.status = 'cancelled'
        order.cancel_reason = "ยกเลิกโดยร้านค้า"
        order.has_unread_status_update = True
        order.save()

        # คืนสต๊อกสินค้า
        for item in order.items.all():
            item.product.stock += item.quantity
            item.product.save()

        messages.success(request, "ยกเลิกคำสั่งซื้อเรียบร้อยแล้ว")
    else:
        messages.error(request, "ไม่สามารถยกเลิกคำสั่งซื้อนี้ได้")

    return redirect("petjoy:orders-detail", order_id=order_id)

@login_required
def handle_cancellation_request(request, order_id):
    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id, customer=request.user.profile)
        cancel_reason = request.POST.get('cancel_reason')
        
        if order.status in ['waiting', 'paid', 'preparing']:
            # คืนสต๊อกสินค้า
            for item in order.items.all():
                item.product.stock += item.quantity
                item.product.save()
            
            # อัปเดตสถานะออเดอร์
            order.status = 'cancelled'
            order.cancel_reason = cancel_reason
            order.save()
            
            messages.success(request, 'ยกเลิกคำสั่งซื้อเรียบร้อยแล้ว')
            
    return redirect('petjoy:order_detail_customer', order_id=order.id)

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
def customer_support_chat(request):
    room, created = CustomerAdminChatRoom.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        msg = request.POST.get('message')
        attachment = request.FILES.get('attachment')
        if msg or attachment:
            CustomerAdminChatMessage.objects.create(
                room=room,
                sender=request.user,
                message=msg,
                attachment=attachment
            )
        return redirect('petjoy:customer-support-chat')
        
    # ✨ จุดสำคัญ: สั่งให้เรนเดอร์ไปที่ chat_room.html ตัวเดิมเลย!
    return render(request, 'petjoy/chat_room.html', {
        'room': room,
        'messages': room.messages.all(),
        'is_support': True  # ส่งตัวแปรนี้ไปบอกเทมเพลตว่านี่คือแชทแอดมิน
    })

@login_required
def delete_support_chat(request, room_id):
    """ฟังก์ชันสำหรับลูกค้าลบห้องแชทของตัวเองที่คุยกับแอดมิน"""
    if request.method == 'POST':
        # หาห้องแชทที่เป็นของ User คนนี้จริงๆ เท่านั้น (ป้องกันคนอื่นมาลบ)
        room = get_object_or_404(CustomerAdminChatRoom, id=room_id, user=request.user)
        room.delete()
        
    # ลบเสร็จแล้วให้เด้งกลับมาที่หน้า Chat List ของลูกค้า
    return redirect('petjoy:chat_list')  

@staff_member_required
def admin_customer_chat_room(request, room_id):
    # แอดมินตอบกลับลูกค้า
    room = get_object_or_404(CustomerAdminChatRoom, id=room_id)
    if request.method == 'POST':
        msg = request.POST.get('message')
        if msg:
            CustomerAdminChatMessage.objects.create(
                room=room,
                sender=request.user,
                message=msg
            )
        return redirect('petjoy:admin-customer-chat-room', room_id=room.id)
    
    # ✨ สิ่งที่เพิ่มเข้ามา: ดึงประวัติข้อความในห้องแชทนี้
    messages_list = room.messages.all().order_by('id')
    
    # ✨ สิ่งที่แก้ไข: เปลี่ยนชื่อไฟล์ HTML และเพิ่มตัวแปรใน { ... }
    return render(request, 'petjoy/admin/admin_chat_room.html', {
        'room': room,
        'messages': messages_list,     # ส่งข้อความไปแสดงบนหน้าจอ
        'current_user': request.user,  # ส่งข้อมูลแอดมิน (คนล็อกอินปัจจุบัน) ไปเช็คฝั่งซ้าย/ขวาของแชท
        'is_customer_chat': True       # ส่งค่านี้ไปบอกหน้าเว็บว่า "นี่คือแชทลูกค้านะ"
    })

@staff_member_required
def admin_delete_customer_chat(request, room_id):
    """ลบห้องแชทระหว่างลูกค้ากับแอดมิน"""
    if request.method == 'POST':
        room = get_object_or_404(CustomerAdminChatRoom, id=room_id)
        room.delete()
    return redirect('petjoy:admin-chat-list')

@login_required
def start_chat_customer(request, user_id, order_id):
    from django.contrib.auth.models import User
    from .models import Order

    customer = get_object_or_404(User, id=user_id)
    order = get_object_or_404(Order, id=order_id)

    # ดึงร้านจาก order โดยตรง
    entrepreneur = order.entrepreneur

    room, created = ChatRoom.objects.get_or_create(
        customer=customer,
        entrepreneur=entrepreneur
    )

    return redirect('petjoy:entrepreneur-chat-room', room_id=room.id)


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
def delete_chat(request, room_id):
    """ฟังก์ชันลบห้องแชท (ฝั่งลูกค้า) - เปลี่ยนเป็นซ่อนแทน"""
    if request.method == 'POST':
        room = get_object_or_404(ChatRoom, id=room_id)
        
        # เช็คว่าเป็นลูกค้าเจ้าของห้อง
        if request.user == room.customer:
            # ⭐ เปลี่ยนจาก room.delete() เป็นการซ่อนแทน
            room.hidden_by_customer = True  
            room.save()
            
            # (Option) ถ้าทั้งคู่ซ่อนแล้ว ค่อยลบจริง
            if room.hidden_by_customer and room.hidden_by_entrepreneur:
                room.delete()
                
            messages.success(request, "ลบแชทเรียบร้อยแล้ว")
        else:
            messages.error(request, "คุณไม่มีสิทธิ์ลบห้องแชทนี้")
            
    return redirect('petjoy:chat_list')

@login_required
def chat_list(request):
    """แสดงรายชื่อห้องแชททั้งหมดสำหรับลูกค้าเท่านั้น"""
    
    if hasattr(request.user, 'entrepreneur'):
        return redirect('petjoy:entrepreneur-chat-list')
        
    rooms = ChatRoom.objects.filter(
        customer=request.user,
        hidden_by_customer=False   # ⭐ เพิ่มตรงนี้
    ).order_by('-id')
    
    # ✨ เพิ่มตรงนี้: ดึงข้อมูลห้องแชทแอดมินของลูกค้ารายนี้
    support_room = CustomerAdminChatRoom.objects.filter(user=request.user).first()
    
    return render(request, 'petjoy/chat_list.html', {
        'rooms': rooms,
        'current_user': request.user,
        'support_room': support_room, # ✨ เพิ่มตรงนี้: ส่งตัวแปรไปให้ HTML
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
        attachment_file = request.FILES.get('attachment')
        
        if message_text or attachment_file:
            ChatMessage.objects.create(
                room=room,
                sender=request.user,
                message=message_text if message_text else None,
                attachment=attachment_file
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
    """แสดงรายชื่อห้องแชททั้งหมดสำหรับผู้ประกอบการ"""
    if not hasattr(request.user, 'entrepreneur'):
        return redirect('petjoy:chat_list')

    entrepreneur = request.user.entrepreneur
    
    # ⭐ เพิ่มเงื่อนไข hidden_by_entrepreneur=False
    rooms = ChatRoom.objects.filter(
        entrepreneur=entrepreneur, 
        hidden_by_entrepreneur=False
    ).order_by('-id')

    context = {
        'rooms': rooms,
        'current_user': request.user,
        'entrepreneur': entrepreneur,
    }
    return render(request, 'petjoy/entrepreneur/entrepreneur_chat_list.html', context)

@login_required
def entrepreneur_chat_room(request, room_id):
    room = get_object_or_404(ChatRoom, id=room_id)

    # ป้องกันคนอื่นแอบเข้าห้องแชท
    if request.user != room.entrepreneur.user:
        return redirect('petjoy:entrepreneur-chat-list')

    entrepreneur = room.entrepreneur

    # Mark as read (อ่านแล้ว) เฉพาะข้อความที่คู่สนทนาส่งมา
    ChatMessage.objects.filter(
        room=room
    ).exclude(sender=request.user).update(is_read=True)

    if request.method == 'POST':
        message_text = request.POST.get('message')
        attachment = request.FILES.get('attachment')

        if message_text or attachment:
            ChatMessage.objects.create(
                room=room,
                sender=request.user,
                message=message_text,
                attachment=attachment
            )

            room.updated_at = timezone.now()
            room.save()

            return redirect('petjoy:entrepreneur-chat-room', room_id=room.id)

    # -------------------------------
    # 🔽 ส่วนที่เพิ่ม: Date Label
    # -------------------------------
    messages_list = room.messages.all().order_by('timestamp')

    from datetime import timedelta

    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    for msg in messages_list:
        msg.local_date = msg.timestamp.astimezone(
            timezone.get_current_timezone()
        ).date()

        if msg.local_date == today:
            msg.date_label = "วันนี้"
        elif msg.local_date == yesterday:
            msg.date_label = "เมื่อวาน"
        else:
            diff = (today - msg.local_date).days
            if diff <= 7:
                msg.date_label = f"{diff} วันที่แล้ว"
            else:
                msg.date_label = msg.local_date.strftime("%d %b %Y")
    # -------------------------------

    quick_replies = entrepreneur.quick_replies.all().order_by('-created_at')

    context = {
        'room': room,
        'messages': messages_list,
        'current_user': request.user,
        'entrepreneur': entrepreneur,
        'quick_replies': quick_replies,
    }

    return render(
        request,
        'petjoy/entrepreneur/entrepreneur_chat_room.html',
        context
    )

@login_required
def entrepreneur_chat_delete(request, room_id):
    """ฟังก์ชันลบห้องแชท (ฝั่งร้านค้า) - เปลี่ยนเป็นซ่อนแทน"""
    room = get_object_or_404(ChatRoom, id=room_id)

    # เช็คว่าเป็นเจ้าของร้านจริง
    if hasattr(request.user, 'entrepreneur') and request.user.entrepreneur == room.entrepreneur:
        # ⭐ เปลี่ยนจาก room.delete() เป็นการซ่อนแทน
        room.hidden_by_entrepreneur = True 
        room.save()

        # (Option) ถ้าทั้งคู่ซ่อนแล้ว ค่อยลบจริง
        if room.hidden_by_customer and room.hidden_by_entrepreneur:
            room.delete()

        messages.success(request, "ลบแชทเรียบร้อยแล้ว")
    else:
        messages.error(request, "คุณไม่มีสิทธิ์ลบแชทนี้")

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

@login_required(login_url='petjoy:login')
def buy_now(request):
    """ฟังก์ชันสั่งซื้อทันที: เพิ่มลงตะกร้าแล้วไปหน้า Checkout เลย"""
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity') or 1)
        
        product = get_object_or_404(Product, id=product_id)

        # 1. เพิ่มลงตะกร้า
        cart_item, created = CartItem.objects.get_or_create(
            user=request.user,
            product=product
        )
        
        if not created:
            cart_item.quantity += quantity
        else:
            cart_item.quantity = quantity
        cart_item.save()

        # 2. Redirect ไปหน้า Checkout
        # ⭐⭐⭐ แก้บรรทัดนี้ครับ (เปลี่ยน checkout_view -> checkout) ⭐⭐⭐
        checkout_url = reverse('petjoy:checkout') 
        
        return redirect(f"{checkout_url}?selected_items={cart_item.id}&checkout_step=1")

    return redirect('petjoy:product-list')

# # สำหรับหน้าสินค้าแมว (ลูกค้าทั่วไป)
# def cat_products_view(request):
#     cat_category = Category.objects.filter(name__iexact='cat').first()
    
#     # ⭐ กรองสินค้า: หมวดแมว + ร้านต้องอยู่ + ร้านไม่โดนแบน + ร้านอนุมัติแล้ว
#     if cat_category:
#         products = Product.objects.filter(
#             category=cat_category,
#             owner__user__isnull=False,
#             owner__user__profile__is_banned=False,
#             owner__verification_status='approved'
#         )
#     else:
#         products = Product.objects.none()

#     # --- Pagination ---
#     per_page = 15
#     paginator = Paginator(products, per_page)
#     page_number = request.GET.get('page') or 1
#     page_obj = paginator.get_page(page_number)

#     # AJAX
#     if request.GET.get('partial') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#         from django.template.loader import render_to_string
#         from django.http import HttpResponse
#         html = render_to_string('petjoy/partials/food_products_grid.html', {
#             'products': page_obj,
#             'page_obj': page_obj,
#             'paginator': paginator,
#             'selected_type': 'cat',
#         })
#         return HttpResponse(html)

#     return render(request, 'petjoy/cat_products.html', {
#         'products': page_obj, 
#         'page_obj': page_obj, 
#         'paginator': paginator
#     })

# # สำหรับหน้าสินค้าสุนัข (ลูกค้าทั่วไป)
# def dog_products_view(request):
#     dog_category = Category.objects.filter(name__iexact='dog').first()
    
#     # ⭐ กรองสินค้า: หมวดหมา + ร้านต้องอยู่ + ร้านไม่โดนแบน + ร้านอนุมัติแล้ว
#     if dog_category:
#         products = Product.objects.filter(
#             category=dog_category,
#             owner__user__isnull=False,
#             owner__user__profile__is_banned=False,
#             owner__verification_status='approved'
#         )
#     else:
#         products = Product.objects.none()

#     # --- Pagination ---
#     per_page = 15
#     paginator = Paginator(products, per_page)
#     page_number = request.GET.get('page') or 1
#     page_obj = paginator.get_page(page_number)

#     # AJAX
#     if request.GET.get('partial') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#         from django.template.loader import render_to_string
#         from django.http import HttpResponse
#         html = render_to_string('petjoy/partials/food_products_grid.html', {
#             'products': page_obj,
#             'page_obj': page_obj,
#             'paginator': paginator,
#             'selected_type': 'dog',
#         })
#         return HttpResponse(html)

#     return render(request, 'petjoy/dog_products.html', {
#         'products': page_obj, 
#         'page_obj': page_obj, 
#         'paginator': paginator
#     })


# def food_products_view(request):
#     typ_raw = request.GET.get('type', '').strip()
#     typ = typ_raw.lower()
    
#     # ⭐ เริ่มต้น Query: ดึงสินค้าทั้งหมด
#     # เงื่อนไข: 
#     # 1. เจ้าของต้องมีตัวตน (ไม่เป็น Null)
#     # 2. ไม่โดนแบน (is_banned=False)
#     # 3. ร้านต้องได้รับการอนุมัติแล้ว (approved) เท่านั้น!
#     products = Product.objects.filter(
#         owner__user__isnull=False,
#         owner__user__profile__is_banned=False,
#         owner__verification_status='approved' 
#     )

#     # แปลงคำค้นหาภาษาไทยเป็น key
#     map_th = {'สุนัข': 'dog', 'หมา': 'dog', 'แมว': 'cat'}
#     if typ in map_th:
#         typ = map_th[typ]

#     # กรณีเลือกประเภทย่อย (หมา/แมว)
#     if typ in ('dog', 'cat'):
#         # กรองจาก products ที่เรา clean มาแล้วข้างบน
#         products = products.filter(food_type=typ)

#         # หากไม่เจอสินค้า ให้ลองหาจากหมวดหมู่ (Backup Logic)
#         if not products.exists():
#             cat = Category.objects.filter(Q(name__iexact=f'food-{typ}') | Q(display_name__icontains=typ)).first()
#             if cat:
#                 # ต้องกรองซ้ำอีกรอบสำหรับ backup logic
#                 products = Product.objects.filter(
#                     category=cat,
#                     owner__user__isnull=False,
#                     owner__user__profile__is_banned=False,
#                     owner__verification_status='approved'
#                 )
#             else:
#                 food_cat = Category.objects.filter(Q(name__iexact='food') | Q(display_name__icontains='อาหาร')).first()
#                 if food_cat:
#                     products = Product.objects.filter(
#                         category=food_cat,
#                         owner__user__isnull=False,
#                         owner__user__profile__is_banned=False,
#                         owner__verification_status='approved'
#                     ).filter(
#                         Q(name__icontains=typ) | Q(features__icontains=typ) | Q(description__icontains=typ)
#                     )
#     else:
#         # กรณีดูทั้งหมด (ไม่ระบุประเภท) -> ดึงหมวดอาหารทั้งหมด
#         food_cat = Category.objects.filter(Q(name__iexact='food') | Q(display_name__icontains='อาหาร')).first()
#         if food_cat:
#             products = products.filter(category=food_cat)

#     # --- ส่วน Pagination (หน้าละ 15 ชิ้น) ---
#     per_page = 15
#     paginator = Paginator(products, per_page)
#     page_number = request.GET.get('page') or 1
#     page_obj = paginator.get_page(page_number)

#     # รองรับ AJAX (Partial Load)
#     if request.GET.get('partial') == '1' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
#         from django.template.loader import render_to_string
#         from django.http import HttpResponse
#         html = render_to_string('petjoy/partials/food_products_grid.html', {
#             'products': page_obj,
#             'page_obj': page_obj,
#             'paginator': paginator,
#             'selected_type': typ_raw,
#         })
#         return HttpResponse(html)

#     return render(request, 'petjoy/food_products.html', {
#         'products': page_obj,
#         'selected_type': typ_raw,
#         'page_obj': page_obj,
#         'paginator': paginator,
#     })
