# petjoy/middleware.py

from django.shortcuts import redirect
from django.urls import reverse
from .models import Profile

class BanCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # ตรวจสอบว่ามี Profile หรือไม่ (กัน Error)
            try:
                profile = request.user.profile
            except Profile.DoesNotExist:
                profile = None

            if profile and profile.is_banned:
                # รายชื่อ URL ที่ยอมให้เข้าได้แม้โดนแบน (เช่น หน้า logout หรือหน้าแจ้งเตือนแบน)
                allowed_paths = [
                    reverse('petjoy:banned-page'),
                    reverse('petjoy:logout'),
                    '/admin/', # อนุญาตให้เข้าหน้า admin ของ django เผื่อ admin โดนแบนเองจะได้แก้ได้ (หรือจะลบออกก็ได้)
                ]

                # ถ้า URL ปัจจุบันไม่อยู่ในข้อยกเว้น ให้ดีดไปหน้า Banned ทันที
                if request.path not in allowed_paths:
                    return redirect('petjoy:banned-page')

        response = self.get_response(request)
        return response