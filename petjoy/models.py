from django.db import models

# Create your models here.
# petjoy/models.py

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True) # หลังจาก () (blank หมายถึงไม่บังคับให้กรอก ถ้าต้องการบังคับแค่ลบมันออก 
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name

class Product(models.Model):
    # เพิ่มตัวเลือกสำหรับหมวดหมู่
    CATEGORY_CHOICES = [
        ('Dog', 'สุนัข'),
        ('Cat', 'แมว'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    # เพิ่มฟิลด์ category เข้าไป
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, default='Dog')
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)

    def __str__(self):
        return self.name