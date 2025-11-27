from .models import CartItem

def cart_count(request):
    if request.user.is_authenticated:
        return {
            "cart_count": CartItem.objects.filter(user=request.user).count()
        }
    return {"cart_count": 0}
