from django import forms

from .models import CommunityPost


class ContactForm(forms.Form):
    name = forms.CharField(label="Ваше имя", max_length=120)
    email = forms.EmailField(label="Email", max_length=254)
    message = forms.CharField(label="Сообщение", max_length=5000, widget=forms.Textarea(attrs={"rows": 5}))
    consent = forms.BooleanField(label="Согласен с политикой конфиденциальности")
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("name", "email", "message"):
            self.fields[name].widget.attrs.update({
                "class": "w-full px-4 py-3 rounded-xl bg-gray-50 border border-gray-200 focus:outline-none focus:border-black text-[14px]",
                "autocomplete": "name" if name == "name" else "email" if name == "email" else "off",
            })

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Не удалось отправить форму.")
        return ""


class CommunityPostForm(forms.ModelForm):
    class Meta:
        model = CommunityPost
        fields = ["title", "text", "image"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "Тема записи",
                    "class": "aspect-community-input",
                }
            ),
            "text": forms.Textarea(
                attrs={
                    "placeholder": "Поделитесь рецептом, впечатлением или вопросом",
                    "rows": 4,
                    "class": "aspect-community-textarea",
                }
            ),
        }
