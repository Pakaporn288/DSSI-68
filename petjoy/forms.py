# petjoy/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Product

# ฟอร์มนี้คือฟอร์มสมัครสมาชิกที่ถูกต้องเพียงอันเดียวที่เราจะใช้
class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ("email",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'ชื่อผู้ใช้'})
        self.fields['email'].widget.attrs.update({'placeholder': 'อีเมล'})
        self.fields['password'].widget.attrs.update({'placeholder': 'รหัสผ่าน'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'ยืนยันรหัสผ่าน'})
        self.fields['username'].label = "ชื่อผู้ใช้"
        self.fields['email'].label = "อีเมล"
        self.fields['password'].label = "รหัสผ่าน"
        self.fields['password2'].label = "ยืนยันรหัสผ่าน"

# ฟอร์มนี้สำหรับสินค้า เก็บไว้ใช้ในอนาคต
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'category', 'image']