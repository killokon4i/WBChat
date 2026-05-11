from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import password_validation
from .models import User

class RegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'department', 'avatar', ]
class ProfileEditForm(forms.ModelForm):
    username = forms.CharField(required=True, label="Имя пользователя (ник)")
    first_name = forms.CharField(required=False, label="Имя")
    last_name = forms.CharField(required=False, label="Фамилия")
    middle_name = forms.CharField(required=False, label="Отчество")
    email = forms.EmailField(required=False, label="Email")
    avatar = forms.ImageField(required=False, label="Аватар")
    remove_avatar = forms.CharField(required=False, widget=forms.HiddenInput)

    old_password = forms.CharField(required=False, widget=forms.PasswordInput, label="Старый пароль")
    new_password = forms.CharField(required=False, widget=forms.PasswordInput, label="Новый пароль")
    confirm_password = forms.CharField(required=False, widget=forms.PasswordInput, label="Подтверждение нового пароля")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "middle_name", "email", "avatar")

    def __init__(self, user, *args, **kwargs):
        self.user = user
        # Передаём instance чтобы Django знал что это редактирование существующего пользователя
        kwargs['instance'] = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()

        old = cleaned.get("old_password")
        new = cleaned.get("new_password")
        confirm = cleaned.get("confirm_password")

        # Если пользователь хочет сменить пароль — проверяем всё
        if old or new or confirm:
            if not old:
                raise forms.ValidationError("Введите старый пароль.")
            if not self.user.check_password(old):
                raise forms.ValidationError("Старый пароль неверный.")
            if not new:
                raise forms.ValidationError("Введите новый пароль.")
            if new != confirm:
                raise forms.ValidationError("Новые пароли не совпадают.")

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # middle_name может быть None, приводим к пустой строке
        if not user.middle_name:
            user.middle_name = ''

        # Если пароль изменяется
        new = self.cleaned_data.get("new_password")
        if new:
            user.set_password(new)
        
        # Обработка аватара
        if self.cleaned_data.get('remove_avatar') == '1':
            # Удаление аватара
            if user.avatar:
                user.avatar.delete(save=False)
                user.avatar = None
        elif self.cleaned_data.get('avatar'):
            # Новый аватар (старый удалится автоматически при перезаписи)
            pass  # avatar уже присвоен через super().save()

        if commit:
            user.save()

        return user