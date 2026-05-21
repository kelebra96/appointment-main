"""
admin.py — Configuração do painel administrativo do Django

O Django Admin é uma interface web gerada automaticamente a partir dos models.
Com poucas linhas de código, temos uma área de administração completa com:
    - Listagem, busca e filtros por qualquer campo
    - Formulários de criação e edição
    - Controle de acesso (apenas is_staff=True)

Para acessar: /admin/  (usuário deve ser superusuário)
Criar superusuário: python manage.py createsuperuser

Cada classe abaixo personaliza como um model é exibido no Admin.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Specialty, Doctor, DoctorAvailability, Appointment


class DoctorAvailabilityInline(admin.TabularInline):
    """
    Inline que permite editar as disponibilidades do médico
    diretamente na página de edição do médico — sem sair da tela.

    TabularInline exibe os registros em formato de tabela (linha a linha).
    """
    model = DoctorAvailability
    extra = 1  # exibe 1 linha extra vazia para facilitar a adição


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Extensão do UserAdmin padrão do Django.

    BaseUserAdmin já cuida de senha (hash), permissões e grupos.
    Adicionamos um fieldset extra com os campos médicos do nosso User.
    """
    list_display  = ['username', 'email', 'first_name', 'last_name', 'phone', 'is_staff', 'is_active']
    list_filter   = ['is_staff', 'is_active', 'blood_type']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'cpf', 'phone']

    # Adiciona seção de "Informações Médicas" ao formulário de edição
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informações Médicas', {
            'fields': ('phone', 'cpf', 'birth_date', 'health_insurance',
                       'health_insurance_number', 'blood_type', 'allergies')
        }),
    )

    # Adiciona campos extras ao formulário de criação de usuário
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informações Adicionais', {
            'fields': ('email', 'first_name', 'last_name', 'phone', 'cpf')
        }),
    )


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    """Admin de especialidades médicas."""
    list_display  = ['name', 'code', 'consultation_price', 'duration']
    search_fields = ['name', 'code']
    list_filter   = ['duration']


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    """
    Admin de médicos com edição inline das disponibilidades.

    O inline permite cadastrar os horários de trabalho do médico
    na mesma tela de cadastro/edição — sem formulários separados.
    """
    list_display  = ['name', 'email', 'crm', 'specialty', 'is_active']
    list_filter   = ['specialty', 'is_active']
    search_fields = ['name', 'email', 'crm']
    inlines       = [DoctorAvailabilityInline]


@admin.register(DoctorAvailability)
class DoctorAvailabilityAdmin(admin.ModelAdmin):
    """Admin de disponibilidades (também acessível diretamente, fora do inline)."""
    list_display = ['doctor', 'day_of_week', 'start_time', 'end_time']
    list_filter  = ['doctor', 'day_of_week']


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """
    Admin de consultas — principal tela de gestão para a clínica.

    date_hierarchy adiciona navegação por ano/mês/dia no topo da listagem.
    readonly_fields impede alterar campos que não devem ser modificados manualmente.
    """
    list_display   = ['patient', 'doctor', 'specialty', 'date', 'time', 'status', 'created_at']
    list_filter    = ['status', 'date', 'specialty', 'doctor']
    search_fields  = ['patient__username', 'patient__first_name', 'patient__last_name',
                      'doctor__name', 'reason']
    date_hierarchy = 'date'          # navegação por período no topo
    readonly_fields= ['created_at']  # data de criação não deve ser editada

    # Organiza os campos em seções lógicas no formulário de edição
    fieldsets = (
        ('Informações da Consulta', {
            'fields': ('patient', 'doctor', 'specialty', 'date', 'time', 'time_end')
        }),
        ('Detalhes', {
            'fields': ('reason', 'notes', 'status', 'notified')
        }),
        ('Sistema', {
            'fields': ('created_at',),
            'classes': ('collapse',)  # seção colapsável — menos destaque
        }),
    )
