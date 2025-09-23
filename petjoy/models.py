# ผู้ประกอบการ (1 user = 1 ร้าน)
from django.conf import settings
from django.db import models
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

    def __str__(self):
        return self.name
    
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default='profile_pics/default.jpg', upload_to='profile_pics')

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
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    store_name = models.CharField(max_length=100)
    owner_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    # เพิ่ม field อื่นๆ ได้ตามต้องการ

    def __str__(self):
        return self.store_name