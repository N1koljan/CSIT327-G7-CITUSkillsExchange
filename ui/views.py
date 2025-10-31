# In ui/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from core.forms import CustomSignUpForm
from core.forms import CustomLoginForm, CustomSignUpForm
from django.contrib.auth import login, logout

from ui.forms import EditProfileForm


def home(request):
    return render(request, 'ui/index.html')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomLoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('dashboard')
    else:
        form = CustomLoginForm()

    return render(request, 'ui/auth/login.html', {'form': form})


def signup_view(request):
    if request.method == 'POST':

        print("✅ POST request received in ui/views.py!")
        form = CustomSignUpForm(request.POST)
        print("Is the form valid?", form.is_valid())
        print("Form Errors:", form.errors.as_json())
        # ----------------------------

        if form.is_valid():
            user = form.save()
            messages.success(request, f'Account for {user.username} created successfully! You can now log in.')
            return redirect('login')
    else:
        form = CustomSignUpForm()

    return render(request, 'ui/auth/signup.html', {'form': form})

@login_required
def profile_view(request):
    context = {
        'user': request.user
    }
    return render(request, 'ui/student/profile.html', context)


@login_required
def dashboard_view(request):
    return render(request, 'ui/student/dashboard.html')

@login_required
def edit_profile_view(request):
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        form = EditProfileForm(instance=request.user)

    context = {
        'form': form
    }
    return render(request, 'ui/student/edit_profile.html', context)

def logout_view(request):
    logout(request)
    messages.info(request, "You have successfully logged out.")
    return redirect('login')

@login_required
def my_skill_view(request):
    return render(request, 'ui/student/my_skills.html')

@login_required
def request_view(request):
    return render(request, 'ui/student/request.html')

@login_required
def find_skill_view(request):
    return render(request, 'ui/student/find_skills.html')

@login_required
def schedule_view(request):
    return render(request, 'ui/student/schedule.html')

@login_required
def notification_view(request):
    return render(request, 'ui/student/notification.html')

@login_required
def chat_view(request):
    return render(request, 'ui/student/chat.html')

def skill_view(request):
    return render(request, 'ui/student/skill.html')
# --------------------------------