from django import forms

from .models import CommunityPost


class CommunityPostForm(forms.ModelForm):
    class Meta:
        model = CommunityPost
        fields = ["title", "text", "image"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "Тема записи",
                    "class": "tc-community-input",
                }
            ),
            "text": forms.Textarea(
                attrs={
                    "placeholder": "Поделитесь рецептом, впечатлением или вопросом",
                    "rows": 4,
                    "class": "tc-community-textarea",
                }
            ),
        }
