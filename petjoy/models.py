from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator



class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100)

    image = models.ImageField(
        upload_to='category_images/',
        null=True,
        blank=True
    )

    def __str__(self):
        return self.display_name


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    features = models.TextField(blank=True, null=True, help_text='คุณสมบัติสินค้า')
    total_stock = models.PositiveIntegerField(default=0, help_text='จำนวนสินค้าทั้งหมด')
    stock = models.PositiveIntegerField(default=0, help_text='จำนวนสินค้าคงเหลือ')

    FOOD_TYPE_CHOICES = (
        ('dog', 'สุนัข'),
        ('cat', 'แมว'),
    )
    food_type = models.CharField(max_length=10, choices=FOOD_TYPE_CHOICES, blank=True, null=True, help_text='สำหรับหมวดอาหาร: ประเภทสัตว์')

    # เจ้าของสินค้า (ผู้ประกอบการ)
    owner = models.ForeignKey(
        'Entrepreneur',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='products'
    )

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    favorites = models.ManyToManyField('Product', blank=True, related_name='favorited_by')

    is_banned = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.username} Profile'


class Review(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    # ✅ แก้เฉพาะตรงนี้
    order = models.ForeignKey(
        "Order",
        on_delete=models.CASCADE,
        related_name='reviews',
        null=True,      # ← เพิ่ม
        blank=True      # ← เพิ่ม
    )

    rating = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'product', 'order')

    def __str__(self):
        return f'Review for {self.product.name} by {self.user.username}'


class ChatHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    user_message = models.TextField()
    ai_response = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat by {self.user.username if self.user else 'Anonymous'} at {self.created_at}"


# models.py

class Entrepreneur(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    store_name = models.CharField(max_length=100)
    owner_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    profile_image = models.ImageField(upload_to='entrepreneur_profiles/', blank=True, null=True)

    # ข้อมูลสำหรับหน้าตั้งค่าและข้อมูลตอนสมัคร
    tax_id = models.CharField(max_length=20, blank=True, null=True)
    shop_address = models.TextField(blank=True, null=True)

    # ข้อมูลบัญชีธนาคาร
    bank_name = models.CharField(max_length=100, blank=True, null=True)
    account_name = models.CharField(max_length=100, blank=True, null=True)
    account_number = models.CharField(max_length=50, blank=True, null=True)

    # ⭐ ฟิลด์สำหรับเอกสารประกอบการสมัคร ⭐
    bank_book_copy = models.ImageField(upload_to='bankbooks/', blank=True, null=True)
    id_card_copy = models.ImageField(upload_to='idcards/', blank=True, null=True)
    # หากมีเอกสารพาณิชย์เพิ่มเติม
    commerce_doc = models.ImageField(upload_to='commerce_docs/', blank=True, null=True) 

    shipping_cost = models.DecimalField(max_digits=6, decimal_places=2, default=0.00, help_text="ค่าจัดส่งเหมาจ่ายของร้าน")

    # ⭐ ส่วนที่เพิ่ม: สถานะการตรวจสอบร้านค้า ⭐
    VERIFICATION_CHOICES = [
        ('pending', 'รอตรวจสอบ'),
        ('approved', 'อนุมัติแล้ว'),
        ('rejected', 'ปฏิเสธ'),
    ]
    verification_status = models.CharField(
        max_length=20, 
        choices=VERIFICATION_CHOICES, 
        default='pending'
    )

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

    @property
    def total_price(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.user} - {self.product} x{self.quantity}"


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
        ("waiting", "รอชำระเงิน"),
        ("paid", "ชำระเงินแล้ว"),
        ("preparing", "กำลังเตรียมของ"),
        ("delivering", "กำลังจัดส่ง"),
        ("success", "สำเร็จ"),

    ]
    # 🔹 ผูกกับลูกค้า (จำเป็นมากสำหรับระบบแชท)
    customer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="orders"
    )

    # 🔹 ผูกกับร้านค้า
    entrepreneur = models.ForeignKey(
        "Entrepreneur",
        on_delete=models.CASCADE,
        related_name="orders",
        null=True,
        blank=True
    )

    order_number = models.IntegerField()

    # 🔹 ข้อมูลจัดส่ง (เก็บ snapshot กันกรณีลูกค้าแก้ไขโปรไฟล์ทีหลัง)
    customer_name = models.CharField(max_length=255)
    customer_phone = models.CharField(max_length=20, null=True, blank=True)
    customer_address = models.TextField(null=True, blank=True)


    shipping_cost = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="waiting"
    )

    slip_image = models.ImageField(
        upload_to="slips/",
        null=True,
        blank=True
    )

    tracking_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    has_unread_status_update = models.BooleanField(default=False)

    def save(self, *args, **kwargs):

        # 🔹 สร้างเลข order แยกตามร้าน
        if not self.order_number:
            last_order = Order.objects.filter(
                entrepreneur=self.entrepreneur
            ).order_by('-order_number').first()

            if last_order:
                self.order_number = last_order.order_number + 1
            else:
                self.order_number = 1

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.order_number} - {self.customer.username}"

        

class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )
    quantity = models.PositiveIntegerField(default=1)

    # ราคาต่อชิ้นตอนที่ลูกค้าสั่ง (กันปัญหาสินค้าปรับราคา)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def total(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class ChatRoom(models.Model):
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_chatrooms')
    entrepreneur = models.ForeignKey('Entrepreneur', on_delete=models.CASCADE, related_name='entrepreneur_chatrooms')
    hidden_by_customer = models.BooleanField(default=False)
    hidden_by_entrepreneur = models.BooleanField(default=False)

    class Meta:
        unique_together = ('customer', 'entrepreneur')

    @property
    def last_message(self):
        return self.messages.order_by('-id').first()

    def __str__(self):
        return f"Chat between {self.customer.username} and {self.entrepreneur.store_name}"


class ChatMessage(models.Model):
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField(blank=True, null=True) # 👈 แก้บรรทัดนี้: ใส่ blank=True, null=True (เผื่อส่งแค่รูป)
    
    # === 👉 เพิ่ม 2 บรรทัดนี้ครับ ===
    attachment = models.FileField(upload_to='chat_attachments/', blank=True, null=True)
    is_read = models.BooleanField(default=False)
    # ==============================

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender.username}: {str(self.message)[:50]}"
    
# models.py

class QuickReply(models.Model):
    entrepreneur = models.ForeignKey(Entrepreneur, on_delete=models.CASCADE, related_name='quick_replies')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message[:50]

class ProductReport(models.Model):
    REPORT_REASONS = [
        ('inappropriate', 'เนื้อหาไม่เหมาะสม'),
        ('scam', 'เข้าข่ายหลอกลวง'),
        ('copyright', 'ละเมิดลิขสิทธิ์'),
        ('other', 'อื่นๆ'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reports')
    reason = models.CharField(max_length=20, choices=REPORT_REASONS)
    details = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

class ReviewReply(models.Model):
    review = models.OneToOneField(
        Review,
        on_delete=models.CASCADE,
        related_name="reply"
    )
    entrepreneur = models.ForeignKey(
        Entrepreneur,
        on_delete=models.CASCADE
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reply to review {self.review.id}"
