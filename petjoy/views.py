from django.shortcuts import render

# Create your views here.

def homepage(request):
    return render(request, 'petjoy/homepage.html')

# views.py
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .ai_service import get_ai_response
from .forms import NewUserForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages  

def ask_ai_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_message = data.get('message')

        if not user_message:
            return JsonResponse({'error': 'No message provided'}, status=400)

        ai_reply = get_ai_response(user_message)
        return JsonResponse({'reply': ai_reply})

    return JsonResponse({'error': 'Invalid request method'}, status=405)

def register_view(request):
    if request.method == "POST":
        form = NewUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "สมัครสมาชิกสำเร็จ!")
            return redirect("petjoy:homepage")
        messages.error(request, "สมัครสมาชิกไม่สำเร็จ กรุณาตรวจสอบข้อมูลอีกครั้ง")
    
    form = NewUserForm()
    return render(request, "petjoy/register.html", context={"register_form": form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.info(request, f"ยินดีต้อนรับกลับมา, {username}")
                return redirect("petjoy:homepage")
            else:
                messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        else:
            messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    form = AuthenticationForm()
    return render(request, "petjoy/login.html", context={"login_form": form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                # 'messages' จะถูกใช้งานตรงนี้
                messages.info(request, f"ยินดีต้อนรับกลับมา, {username}")
                return redirect("petjoy:homepage")
            else:
                # และตรงนี้
                messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
        else:
            # และตรงนี้
            messages.error(request, "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")

    form = AuthenticationForm()
    return render(request, "petjoy/login.html", context={"login_form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "คุณได้ออกจากระบบแล้ว")
    return redirect("petjoy:homepage")


