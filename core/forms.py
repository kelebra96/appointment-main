"""
forms.py — Formulários da aplicação AgendaMed

Os formulários do Django têm duas funções principais:
    1. Renderizar campos HTML no template (via {{ form.as_p }} ou campo a campo)
    2. Validar os dados enviados pelo usuário no POST

Tipos usados neste arquivo:
    - forms.Form       → formulário genérico (não ligado a um model)
    - ModelForm        → gerado automaticamente a partir de um model
    - UserCreationForm → formulário do próprio Django para criar usuários
                         (já cuida de hash de senha, confirmação, etc.)
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User


class UserRegistrationForm(UserCreationForm):
    """
    Formulário de cadastro de paciente.

    Estende UserCreationForm do Django, que já inclui:
        - Campo password1 (senha)
        - Campo password2 (confirmação de senha)
        - Validação de força da senha
        - Geração do hash seguro da senha (nunca salva em texto puro)

    Adicionamos campos extras específicos para o contexto médico:
        email, cpf, phone, birth_date, health_insurance, blood_type, allergies

    Validações customizadas:
        clean_cpf()   → verifica se o CPF já está cadastrado
        clean_email() → verifica se o e-mail já está em uso
    """

    # Campos de identificação — obrigatórios
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'E-mail'
        })
    )
    first_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nome'
        })
    )
    last_name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Sobrenome'
        })
    )
    phone = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Telefone (00) 00000-0000'
        })
    )
    cpf = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'CPF 000.000.000-00'
        })
    )

    # Campos médicos — opcionais
    birth_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'  # renderiza o seletor de data nativo do browser
        })
    )
    health_insurance = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Convenio'
        })
    )
    health_insurance_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Numero do Convenio'
        })
    )
    blood_type = forms.ChoiceField(
        required=False,
        # Pega as choices diretamente do model para evitar duplicação
        choices=[('', 'Tipo Sanguineo')] + User.BLOOD_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    allergies = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'placeholder': 'Alergias',
            'rows': 3
        })
    )

    class Meta:
        model  = User
        fields = [
            'username', 'email', 'first_name', 'last_name',
            'phone', 'cpf', 'birth_date', 'health_insurance',
            'health_insurance_number', 'blood_type', 'allergies',
            'password1', 'password2'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Aplica Bootstrap nos campos herdados do UserCreationForm
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nome de usuario'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Senha'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirmar senha'
        })

    def clean_cpf(self):
        """Valida que o CPF não está sendo usado por outro paciente."""
        cpf = self.cleaned_data.get('cpf')
        if cpf and User.objects.filter(cpf=cpf).exists():
            raise forms.ValidationError('Este CPF ja esta cadastrado.')
        return cpf

    def clean_email(self):
        """Valida que o e-mail não está sendo usado por outro usuário."""
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este e-mail ja esta cadastrado.')
        return email


class LoginForm(forms.Form):
    """
    Formulário de login por e-mail + senha.

    Usamos forms.Form (não ModelForm) porque login não cria nem atualiza
    nenhum registro — apenas valida credenciais.

    A autenticação real acontece na view login_view(), que:
        1. Usa este form para receber e validar os dados
        2. Busca o usuário pelo e-mail no banco
        3. Chama authenticate() com username + password
    """
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'E-mail'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Senha'
        })
    )
