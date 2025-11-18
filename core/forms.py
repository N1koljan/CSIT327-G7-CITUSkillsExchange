from django import forms
from .models import CustomUser, Request, Skill, Comment, BarterProposal, Rating
from django.db.models import Q

DEPARTMENT_MAPPING = {
    'computer-science': 'CS',
    'information-technology': 'IT',
    'engineering': 'EN',
    'business': 'BA',
    'education': 'ED',
    'arts-sciences': 'AS',
    'architecture': 'AR',
    'nursing': 'NU',
    'maritime': 'MS',
    'other': 'OT',
}


class CustomLoginForm(forms.Form):
    email_or_username = forms.CharField(max_length=254)
    password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        email_or_username = cleaned_data.get('email_or_username')
        password = cleaned_data.get('password')
        self.user_cache = None

        if email_or_username and password:
            try:
                user = CustomUser.objects.get(
                    Q(username=email_or_username) | Q(email=email_or_username)
                )
            except CustomUser.DoesNotExist:
                user = None

            if user:
                if user.check_password(password):
                    self.user_cache = user
                else:
                    raise forms.ValidationError("Invalid username/email or password.")
            else:
                raise forms.ValidationError("Invalid username/email or password.")
        return cleaned_data

    def get_user(self):
        return self.user_cache


class CustomSignUpForm(forms.Form):
    firstName = forms.CharField(max_length=150, required=True)
    lastName = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=True)
    username = forms.CharField(max_length=150, required=True)
    schoolId = forms.CharField(max_length=20, required=True)

    department = forms.ChoiceField(choices=[(k, v.replace('-', ' ').title()) for k, v in DEPARTMENT_MAPPING.items()],
                                   required=True)

    password = forms.CharField(widget=forms.PasswordInput, required=True)
    confirmPassword = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirmPassword")

        if password and confirm_password and password != confirm_password:
            self.add_error('confirmPassword', "Passwords do not match.")

        return cleaned_data

    def save(self):
        data = self.cleaned_data
        user = CustomUser.objects.create_user(
            username=data['username'],
            email=data['email'],
            first_name=data['firstName'],
            last_name=data['lastName'],
            school_id=data['schoolId'],
            department=DEPARTMENT_MAPPING[data['department']],
            password=data['password']
        )
        return user


class SkillRequestForm(forms.ModelForm):
    class Meta:
        model = Request
        fields = ['requested_date_time', 'payment_choice', 'extra_description']
        widgets = {
            'payment_choice': forms.Select(),
            'extra_description': forms.Textarea(
                attrs={
                    'rows': 4,
                    'placeholder': 'Hi! I would like to request help with this skill because...'
                }
            ),
        }
        labels = {
            'requested_date_time': 'Proposed Date & Time',
            'payment_choice': 'Payment Method',
            'extra_description': 'Extra Description',
        }

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Add a comment or ask a question...'
            })
        }
        labels = {
            'content': '',
        }

class BarterProposalForm(forms.ModelForm):
    class Meta:
        model = BarterProposal
        fields = ['offered_skill']
        labels = {
            'offered_skill': 'Select one of your skills to offer in exchange'
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            self.fields['offered_skill'].queryset = Skill.objects.filter(owner=user)

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'type': 'number',
                'min': '1',
                'max': '5',
                'class': 'rating-stars'
            }),
            'comment': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Share your experience with this exchange...'
            })
        }
        labels = {
            'rating': 'Your Rating (1-5 stars)',
            'comment': 'Your Feedback'
        }