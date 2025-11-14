# in ui/forms.py

from django import forms
# --- FIX #1: The 'Request' model is now correctly imported ---
from core.models import CustomUser, Skill, Request

# --- Your Existing EditProfileForm ---
class EditProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ('first_name', 'last_name', 'email', 'school_id', 'department', 'bio', 'profile_picture')
        widgets = {
            # ... your widgets ...
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email'}),
            'school_id': forms.TextInput(attrs={'placeholder': 'School ID'}),
            'department': forms.Select(),
            'bio': forms.Textarea(attrs={'placeholder': 'Write something about yourself...', 'rows': 4}),
            'profile_picture': forms.FileInput(),
        }

# --- FORM FOR SKILL MANAGEMENT ---
class SkillForm(forms.ModelForm):
    """
    Form for creating and editing a Skill.
    """
    class Meta:
        model = Skill
        fields = ['title', 'description', 'category', 'exchange_type']
        widgets = {
            # ... your widgets ...
            'title': forms.TextInput(attrs={'class': '...'}) # Truncated for brevity
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

