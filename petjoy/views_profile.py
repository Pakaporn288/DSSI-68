from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def profile_view(request):
    profile = request.user.profile
    return render(request, 'petjoy/profile.html', {'profile': profile})
