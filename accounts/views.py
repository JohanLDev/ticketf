from django.contrib.auth import login
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.shortcuts import render, redirect
from django.views import View
from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class SimpleLoginForm(forms.Form):
    email = forms.EmailField(label="Email")
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)

class LoginView(DjangoLoginView):
    template_name = "accounts/login.html"
    # El AuthenticationForm usa el campo 'username', pero internamente respeta USERNAME_FIELD
    # Mapeamos el input 'email' al name 'username' en el template.
    # Por eso no seteamos authentication_form aquí.

class LogoutView(DjangoLogoutView):
    pass

class RegisterForm(forms.ModelForm):
    password = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ["email"]
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class RegisterView(View):
    def get(self, request):
        return render(request, "accounts/register.html", {"form": RegisterForm()})
    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("public:home")
        return render(request, "accounts/register.html", {"form": form})
