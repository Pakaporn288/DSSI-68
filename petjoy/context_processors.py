from .models import CartItem
from .models import Order, Address
from django.db.models import Q

def cart_count(request):
    if request.user.is_authenticated:
        return {
            "cart_count": CartItem.objects.filter(user=request.user).count()
        }
    return {"cart_count": 0}

def notification_count(request):
    if not request.user.is_authenticated:
        return {"notification_count": 0}

    # match order ของ user (ชื่อ + เบอร์ เหมือน order_history)
    addresses = Address.objects.filter(user=request.user)
    q = Q()
    for addr in addresses:
        q |= Q(customer_name=addr.full_name, customer_phone=addr.phone)

    count = Order.objects.filter(
        q,
        has_unread_status_update=True
    ).count()

    return {"notification_count": count}
