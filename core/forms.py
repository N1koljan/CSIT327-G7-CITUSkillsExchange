# in core/forms.py

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

    # The choices for this field must match the <option> values in your HTML
    department = forms.ChoiceField(choices=[(k, v.replace('-', ' ').title()) for k, v in DEPARTMENT_MAPPING.items()],
                                   required=True)

    password = forms.CharField(widget=forms.PasswordInput, required=True)
    confirmPassword = forms.CharField(widget=forms.PasswordInput, required=True)

    def clean_username(self):
        # Check if the username is already taken
        username = self.cleaned_data.get('username')
        if CustomUser.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with that username already exists.")
        return username

    def clean_email(self):
        # Check if the email is already in use
        email = self.cleaned_data.get('email')
        if CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    # 👇 THIS FIXES YOUR ERROR
    def clean_schoolId(self):
        schoolId = self.cleaned_data.get('schoolId')
        # Check if the school_id already exists in the database
        if CustomUser.objects.filter(school_id=schoolId).exists():
            raise forms.ValidationError("A user with this School ID already exists.")
        return schoolId

    def clean(self):
        # This method is for cross-field validation
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

        # 👇 MODIFIED: Include the new fields
        fields = ['requested_date_time', 'payment_choice', 'extra_description']

        widgets = {
            # This makes the datetime field use a text input compatible with calendar widgets

            'payment_choice': forms.Select(),  # Use a dropdown for choices
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
                # The user only needs to provide the content.
                # The 'skill' and 'author' will be set automatically in the view.
                fields = ['content']
                widgets = {
                    'content': forms.Textarea(attrs={
                        'rows': 3,
                        'placeholder': 'Add a comment or ask a question...'
                    })
                }
                # Hide the label for the content field to make the UI cleaner
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
        # We need the user to filter the queryset of offered_skill
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            # This is the key part: only show skills owned by the current user.
            self.fields['offered_skill'].queryset = Skill.objects.filter(owner=user)


class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['rating', 'comment']
        widgets = {
            # Hidden input since we use custom star rating in the modal
            'rating': forms.HiddenInput(attrs={
                'id': 'rating_value'
            }),
            'comment': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Share your thoughts about the tutoring session...',
                'class': 'form-textarea'
            })
        }
        labels = {
            'rating': 'Overall Rating',
            'comment': 'Your Review'
        }

    def clean_rating(self):
        """Validate that rating is between 1 and 5"""
        rating = self.cleaned_data.get('rating')
        if rating and (rating < 1 or rating > 5):
            raise forms.ValidationError('Rating must be between 1 and 5 stars.')
        return rating

    def clean_comment(self):
        """Validate that comment is not empty and has minimum length"""
        comment = self.cleaned_data.get('comment')
        if comment:
            # Strip whitespace
            comment = comment.strip()
            if len(comment) < 10:
                raise forms.ValidationError('Please provide a more detailed review (at least 10 characters).')
        return comment
