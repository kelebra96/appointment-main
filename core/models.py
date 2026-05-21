"""
models.py — Camada de dados do AgendaMed (ORM)

Define todos os models da aplicação. Cada model é uma tabela no banco de dados.
O Django ORM traduz automaticamente as classes Python em SQL — nenhuma query
manual é necessária.

Hierarquia de dependências:
    User  ←  Appointment  →  Doctor  →  Specialty
                                ↓
                        DoctorAvailability
"""

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from decimal import Decimal


class User(AbstractUser):
    """
    Model de Usuário customizado — estende o User padrão do Django.

    Por que AbstractUser e não o User padrão?
    O Django oferece um sistema de autenticação pronto (login, logout, sessão,
    permissões). AbstractUser nos permite HERDAR tudo isso e adicionar campos
    extras sem reescrever a lógica de segurança.

    ATENÇÃO: AUTH_USER_MODEL = 'core.User' precisa estar no settings.py
    ANTES da primeira migration. Trocar depois exige recriar o banco inteiro.

    Campos herdados do AbstractUser:
        username, password, email, first_name, last_name,
        is_staff, is_active, is_superuser, date_joined
    """

    BLOOD_TYPE_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'),  ('O-', 'O-'),
    ]

    # Dados de contato
    phone = models.CharField('Telefone', max_length=20, blank=True)

    # CPF como identificador único do paciente no sistema
    cpf = models.CharField('CPF', max_length=14, unique=True, blank=True, null=True)

    # Informações médicas opcionais — preenchidas no cadastro
    birth_date             = models.DateField('Data de Nascimento', blank=True, null=True)
    health_insurance       = models.CharField('Convênio', max_length=100, blank=True)
    health_insurance_number= models.CharField('Número do Convênio', max_length=50, blank=True)
    blood_type             = models.CharField('Tipo Sanguíneo', max_length=3, choices=BLOOD_TYPE_CHOICES, blank=True)
    allergies              = models.TextField('Alergias', blank=True)

    # Campos reservados para futura recuperação de senha por token
    reset_token        = models.CharField(max_length=100, blank=True, null=True)
    reset_token_expire = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name        = 'Usuário'
        verbose_name_plural = 'Usuários'

    def __str__(self):
        # Exibe nome completo no admin; cai para username se não tiver nome
        return self.get_full_name() or self.username

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class Specialty(models.Model):
    """
    Especialidade médica oferecida pela clínica.

    Exemplos: Cardiologia, Dermatologia, Ortopedia.

    O campo `duration` define quanto tempo cada consulta dessa especialidade
    dura — usado pelo DoctorService para calcular os slots de horário disponíveis.
    """

    # UUID garante um código único mesmo antes de salvar no banco
    code = models.UUIDField('Código', default=uuid.uuid4, editable=False, unique=True)

    name               = models.CharField('Nome', max_length=100)
    consultation_price = models.DecimalField(
        'Preço da Consulta',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))]  # preço não pode ser negativo
    )
    duration    = models.PositiveIntegerField('Duração (minutos)', default=30)
    description = models.TextField('Descrição', blank=True)

    class Meta:
        verbose_name        = 'Especialidade'
        verbose_name_plural = 'Especialidades'
        ordering            = ['name']

    def __str__(self):
        return self.name


class Doctor(models.Model):
    """
    Médico que atende na clínica.

    Cada médico pertence a UMA especialidade (ForeignKey).
    As disponibilidades (dias/horários de trabalho) ficam em DoctorAvailability.

    on_delete=PROTECT em specialty: impede deletar uma especialidade
    que ainda tem médicos vinculados — evita dados órfãos.
    """

    name  = models.CharField('Nome', max_length=100)
    email = models.EmailField('E-mail', unique=True)
    phone = models.CharField('Telefone', max_length=20)
    crm   = models.CharField('CRM', max_length=20, unique=True)

    specialty = models.ForeignKey(
        Specialty,
        on_delete=models.PROTECT,  # bloqueia exclusão de Specialty com médicos
        related_name='doctors',
        verbose_name='Especialidade'
    )

    # Soft-delete: desativar ao invés de excluir preserva histórico de consultas
    is_active = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name        = 'Médico'
        verbose_name_plural = 'Médicos'
        ordering            = ['name']

    def __str__(self):
        return f"Dr(a). {self.name} - {self.specialty.name}"


class DoctorAvailability(models.Model):
    """
    Disponibilidade semanal de um médico (dias e horários de trabalho).

    Cada registro representa um bloco de atendimento:
        Ex: Dr. João — Segunda-feira, das 08:00 às 12:00

    O DoctorService usa esses registros para calcular quais horários
    ainda estão livres para agendamento em uma data específica.

    unique_together garante que o mesmo médico não tenha dois registros
    iguais de disponibilidade no mesmo dia/hora.
    """

    DAYS_OF_WEEK = [
        (0, 'Domingo'),
        (1, 'Segunda-feira'),
        (2, 'Terça-feira'),
        (3, 'Quarta-feira'),
        (4, 'Quinta-feira'),
        (5, 'Sexta-feira'),
        (6, 'Sábado'),
    ]

    doctor     = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,  # disponibilidades somem junto com o médico
        related_name='availabilities',
        verbose_name='Médico'
    )
    day_of_week = models.IntegerField('Dia da Semana', choices=DAYS_OF_WEEK)
    start_time  = models.TimeField('Hora de Início')
    end_time    = models.TimeField('Hora de Término')

    class Meta:
        verbose_name        = 'Disponibilidade'
        verbose_name_plural = 'Disponibilidades'
        ordering            = ['day_of_week', 'start_time']
        unique_together     = ['doctor', 'day_of_week', 'start_time']

    def __str__(self):
        return f"{self.doctor.name} - {self.get_day_of_week_display()} ({self.start_time} - {self.end_time})"


class Appointment(models.Model):
    """
    Consulta agendada — model central da aplicação.

    Conecta três entidades: paciente (User), médico (Doctor) e
    especialidade (Specialty). Armazena data, horário, motivo e status.

    Ciclo de vida do status:
        agendado → confirmado → realizado
                ↘ cancelado

    on_delete=PROTECT em doctor e specialty: impede deletar médico ou
    especialidade que tenham consultas no histórico.
    """

    STATUS_CHOICES = [
        ('agendado',  'Agendado'),
        ('confirmado','Confirmado'),
        ('cancelado', 'Cancelado'),
        ('realizado', 'Realizado'),
    ]

    # Chaves estrangeiras — relacionamentos com outras tabelas
    patient   = models.ForeignKey(
        User,
        on_delete=models.CASCADE,   # se o paciente for deletado, suas consultas somem
        related_name='appointments',
        verbose_name='Paciente'
    )
    doctor    = models.ForeignKey(
        Doctor,
        on_delete=models.PROTECT,   # não permite deletar médico com consultas
        related_name='appointments',
        verbose_name='Médico'
    )
    specialty = models.ForeignKey(
        Specialty,
        on_delete=models.PROTECT,   # não permite deletar especialidade com consultas
        related_name='appointments',
        verbose_name='Especialidade'
    )

    # Dados da consulta
    date     = models.DateField('Data')
    time     = models.TimeField('Hora de Início')
    time_end = models.TimeField('Hora de Término')  # calculado automaticamente pelo Service
    reason   = models.TextField('Motivo da Consulta')
    notes    = models.TextField('Observações', blank=True)  # notas do médico

    status   = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='agendado')
    notified = models.BooleanField('Notificado', default=False)

    # auto_now_add=True: preenchido automaticamente com a data/hora atual ao criar
    created_at = models.DateTimeField('Criado em', auto_now_add=True)

    class Meta:
        verbose_name        = 'Consulta'
        verbose_name_plural = 'Consultas'
        ordering            = ['-date', '-time']  # mais recentes primeiro

    def __str__(self):
        return f"{self.patient} - {self.doctor.name} - {self.date} {self.time}"

    @property
    def status_display(self):
        """Retorna o label legível do status atual (ex: 'agendado' → 'Agendado')."""
        return dict(self.STATUS_CHOICES).get(self.status, self.status)

    @property
    def can_cancel(self):
        """Indica se a consulta ainda pode ser cancelada pelo paciente."""
        return self.status in ['agendado', 'confirmado']
