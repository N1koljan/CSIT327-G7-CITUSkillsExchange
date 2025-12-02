# in ui/forms.py

from django import forms
from core.models import CustomUser, Skill, Request


# --- UPDATED EditProfileForm ---
class EditProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        # 👇 CHANGED: Removed 'profile_picture', Added 'username'
        fields = ('first_name', 'last_name', 'username', 'email', 'school_id', 'department', 'bio')

        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),

            # 👇 NEW: Added widget for username
            'username': forms.TextInput(attrs={'placeholder': 'Username'}),

            'email': forms.EmailInput(attrs={'placeholder': 'Email', 'readonly': 'readonly'}),
            # Usually email is read-only
            'school_id': forms.TextInput(attrs={'placeholder': 'School ID', 'readonly': 'readonly'}),
            'department': forms.Select(),
            'bio': forms.Textarea(attrs={'placeholder': 'Write something about yourself...', 'rows': 4}),
        }

    # 👇 NEW: Unique validation logic
    def clean_username(self):
        username = self.cleaned_data.get('username')

        # Check if the username exists in the database
        # .exclude(pk=self.instance.pk) ensures we don't throw an error
        # if the user submits the form with their OWN current username.
        if CustomUser.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A user with that username already exists.")

        return username


# --- FORM FOR SKILL MANAGEMENT (Unchanged) ---
class SkillForm(forms.ModelForm):
    class Meta:
        model = Skill
        fields = ['title', 'description', 'category', 'exchange_type']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Python Programming'}),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe what you can teach...'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'exchange_type': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_title(self):
        title = self.cleaned_data.get('title')
        if not self.user:
            return title
        query = Skill.objects.filter(owner=self.user, title__iexact=title)
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)
        if query.exists():
            raise forms.ValidationError("You already have a skill with this title.")
        return title