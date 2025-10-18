# petjoy/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Product
from django.contrib.auth.models import User
from .models import Profile


class UserUpdateForm(forms.ModelForm):
    first_name = forms.CharField(required=False, label='ชื่อ')
    last_name = forms.CharField(required=False, label='นามสกุล')
    email = forms.EmailField(required=True, label='อีเมล์')
    password = forms.CharField(required=False, widget=forms.PasswordInput, label='เปลี่ยนรหัสผ่าน')

    class Meta:
        model = User
        # Do not include 'password' in the Meta.fields: we handle password updates
        # manually in the view using set_password(). If 'password' is present here,
        # form.save() will overwrite the hashed password with the raw value (or blank).
        fields = ['first_name', 'last_name', 'email']


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['image']

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
            username = username.strip()
            # Ensure username uniqueness (case-insensitive)
            if User.objects.filter(username__iexact=username).exists():
                raise forms.ValidationError("ชื่อผู้ใช้นี้ถูกใช้งานแล้ว โปรดเลือกชื่ออื่น")
        return username

# ฟอร์มนี้สำหรับสินค้า เก็บไว้ใช้ในอนาคต
class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'description', 'features', 'price', 'category', 'image', 'total_stock', 'stock', 'food_type']

    def clean(self):
        cleaned = super().clean()
        category = cleaned.get('category')
        food_type = cleaned.get('food_type')
        cat_name = category.display_name.lower() if category and category.display_name else ''
        if 'อาหาร' in cat_name or 'food' in cat_name:
            # If category is food, require food_type to be selected
            if not food_type:
                raise forms.ValidationError('กรุณาเลือกประเภทสัตว์ (สุนัข/แมว) สำหรับหมวดอาหาร')
        return cleaned
