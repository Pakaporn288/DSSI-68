from django.conf import settings
from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)

    def __str__(self):
        return self.display_name
 
class Product(models.Model):
    name = models.CharField(max_length=200) #ชื่อสินค้าขนาดไม่เกิน 200 ตัวอักษร
    description = models.TextField(blank=True, null=True) #รายละเอียดสินค้า สามารถเว้นว่างได้
    price = models.DecimalField(max_digits=10, decimal_places=2)#ราคาสินค้า มีทศนิยม 2 ตำแหน่ง สูงสุด 10 หลัก
    category = models.ForeignKey(Category, on_delete=models.CASCADE)#หมวดหมู่ของสินค้าเชื่อมโยงกับโมเดล Category
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)#รูปภาพสินค้า สามารถเว้นว่างได้ และจัดเก็บในโฟลเดอร์ 'product_images/'
    features = models.TextField(blank=True, null=True, help_text='คุณสมบัติสินค้า')# คุณสมบัติเด่นของสินค้า เช่น วัสดุ ขนาด สี เป็นต้น
    total_stock = models.PositiveIntegerField(default=0, help_text='จำนวนสินค้าทั้งหมด')# จำนวนสินค้าทั้งหมดที่มีในสต็อก
    stock = models.PositiveIntegerField(default=0, help_text='จำนวนสินค้าคงเหลือ') #จำนวนสินค้าคงเหลือที่สามารถขายได้
    # If the product is a pet food, the seller can mark whether it's for dog or cat.
    FOOD_TYPE_CHOICES = (
        ('dog', 'สุนัข'),
        ('cat', 'แมว'),
    )
    food_type = models.CharField(max_length=10, choices=FOOD_TYPE_CHOICES, blank=True, null=True, help_text='สำหรับหมวดอาหาร: ประเภทสัตว์ (สุนัข/แมว)')
    # Owner of the product (the entrepreneur who owns this product). Nullable for existing rows.
    owner = models.ForeignKey('Entrepreneur', null=True, blank=True, on_delete=models.SET_NULL, related_name='products')

    def __str__(self):
        return self.name
    
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Remove hard-coded default file path. Use blank/null so templates can
    # provide a static fallback when no image is uploaded.
    image = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    # Users can favorite products; only registered users have a Profile
    favorites = models.ManyToManyField('Product', blank=True, related_name='favorited_by')

    def __str__(self):
        return f'{self.user.username} Profile'

class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5) # คะแนน (ยังไม่ใช้ตอนนี้)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Review for {self.product.name} by {self.user.username}'
    
class ChatHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    user_message = models.TextField()
    ai_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat by {self.user.username if self.user else 'Anonymous'} at {self.created_at}"

# class Entrepreneur(models.Model):
#     user = models.OneToOneField(User, on_delete=models.CASCADE)
#     store_name = models.CharField(max_length=100)
#     owner_name = models.CharField(max_length=100)
#     email = models.EmailField()
#     phone = models.CharField(max_length=20)

#     def __str__(self):
#         return self.store_name
    
class Entrepreneur(models.Model):
    # Allow entrepreneur records to exist without a linked User account.
    user = models.OneToOneField(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    store_name = models.CharField(max_length=100)
    owner_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    profile_image = models.ImageField(upload_to='entrepreneur_profiles/', blank=True, null=True)
    # เพิ่ม field อื่นๆ ได้ตามต้องการ

    def __str__(self):
        return self.store_name
    
class CartItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f"{self.user} - {self.product} x{self.quantity}"

    @property
    def total_price(self):
        return self.product.price * self.quantity
    
class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    address_line = models.TextField()
    province = models.CharField(max_length=50)
    district = models.CharField(max_length=50)
    subdistrict = models.CharField(max_length=50)
    zipcode = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.full_name} - {self.address_line}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('waiting', 'รอชำระเงิน'),
        ('paid', 'ชำระเงินแล้ว'),
        ('preparing', 'กำลังจัดเตรียม'),
        ('delivering', 'กำลังจัดส่ง'),
        ('success', 'สำเร็จ'),
    ]

    entrepreneur = models.ForeignKey("Entrepreneur", on_delete=models.CASCADE)
    order_number = models.PositiveIntegerField(default=0)
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=50)
    customer_address = models.TextField()

    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):   # ⭐ เพิ่มตรงนี้
        if self.order_number == 0:
            last_order = Order.objects.filter(
                entrepreneur=self.entrepreneur
            ).order_by('-order_number').first()

            if last_order:
                self.order_number = last_order.order_number + 1
            else:
                self.order_number = 1

        super().save(*args, **kwargs)



class OrderItem(models.Model):
    order = models.ForeignKey("Order", on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("Product", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def get_total(self):
        return self.quantity * self.price
    
class ChatRoom(models.Model):
    """ห้องแชทระหว่างลูกค้ากับผู้ประกอบการ"""
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_chatrooms')
    entrepreneur = models.ForeignKey('Entrepreneur', on_delete=models.CASCADE, related_name='entrepreneur_chatrooms')
    
    # อาจจะเพิ่ม 'order' field เพื่อผูกกับ Order ใด Order หนึ่งโดยเฉพาะ

    class Meta:
        unique_together = ('customer', 'entrepreneur')

    def __str__(self):
        return f"Chat between {self.customer.username} and {self.entrepreneur.store_name}"

    # --- ส่วนที่เพิ่มเข้ามา เพื่อให้หน้า Chat List ดึงข้อความล่าสุดได้ถูกต้อง ---
    @property
    def last_message(self):
        """ดึงข้อความล่าสุดของห้องนี้"""
        return self.messages.order_by('-id').first()
    # -------------------------------------------------------------

class ChatMessage(models.Model):
    """ข้อความในห้องแชท"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
        
    def __str__(self):
        return f"{self.sender.username}: {self.message[:50]}"