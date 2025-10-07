# petjoy/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Product

# ฟอร์มนี้คือฟอร์มสมัครสมาชิกที่ถูกต้องเพียงอันเดียวที่เราจะใช้
class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    # Override username to allow Unicode characters (e.g., Thai) and avoid the
    # default restrictive validator that disallows non ASCII characters.
    username = forms.CharField(max_length=150, required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ("email",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'placeholder': 'ชื่อผู้ใช้'})
        self.fields['email'].widget.attrs.update({'placeholder': 'อีเมล'})
        self.fields['password1'].widget.attrs.update({'placeholder': 'รหัสผ่าน'})
        self.fields['password2'].widget.attrs.update({'placeholder': 'ยืนยันรหัสผ่าน'})
        self.fields['username'].label = "ชื่อผู้ใช้"
        self.fields['email'].label = "อีเมล"
        self.fields['password1'].label = "รหัสผ่าน"
        self.fields['password2'].label = "ยืนยันรหัสผ่าน"

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Ensure username uniqueness (case-insensitive)
            if User.objects.filter(username__iexact=username).exists():
                raise forms.ValidationError("ชื่อผู้ใช้นี้ถูกใช้งานแล้ว โปรดเลือกชื่ออื่น")
        return username

# ฟอร์มนี้สำหรับสินค้า เก็บไว้ใช้ในอนาคต
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'features', 'price', 'category', 'image', 'total_stock', 'stock']
