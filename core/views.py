"""
views.py — Controladores da aplicação AgendaMed

No padrão MVT do Django, as views são responsáveis por:
    1. Receber a requisição HTTP do usuário
    2. Executar a lógica necessária (consultar banco, validar dados, etc.)
    3. Devolver uma resposta HTTP (renderizar um template ou redirecionar)

Estrutura deste arquivo:
    - Views públicas:      home, login_view, register, logout_view
    - Views autenticadas:  appointment_create, appointment_list,
                           appointment_cancel, service_list

Decoradores usados:
    @login_required  — redireciona para /login/ se o usuário não estiver logado
    @require_POST    — retorna erro 405 se a requisição não for POST
"""

from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST

from .models import User, Specialty, Appointment, DoctorAvailability
from .forms import UserRegistrationForm, LoginForm
from .services import AppointmentService, DoctorService


# ============================================================================
# VIEWS PÚBLICAS — acessíveis sem estar logado
# ============================================================================

def home(request):
    """
    Página inicial da aplicação.
    Renderiza o template de boas-vindas com links para login e cadastro.
    """
    return render(request, 'core/home.html')


def login_view(request):
    """
    Autenticação do usuário por e-mail e senha.

    O Django autentica internamente por username. Como queremos login por
    e-mail, primeiro buscamos o User pelo e-mail para obter o username,
    depois chamamos authenticate() com esse username.

    Fluxo:
        GET  → exibe o formulário de login vazio
        POST → valida credenciais → redireciona para home (ou ?next=)
    """
    # Usuário já logado não precisa ver a tela de login
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email    = form.cleaned_data['email']
            password = form.cleaned_data['password']

            try:
                # Passo 1: busca o usuário pelo e-mail
                user = User.objects.get(email=email)

                # Passo 2: autentica usando o username (padrão interno do Django)
                user = authenticate(request, username=user.username, password=password)

                if user is not None:
                    login(request, user)  # cria a sessão do usuário
                    messages.success(request, 'Login realizado com sucesso!')

                    # Respeita o parâmetro ?next= (redireciona para a página que o
                    # usuário tentou acessar antes de ser mandado pro login)
                    next_url = request.GET.get('next', 'home')
                    return redirect(next_url)
                else:
                    messages.error(request, 'E-mail ou senha invalidos.')

            except User.DoesNotExist:
                # Mesma mensagem de erro para não revelar se o e-mail existe ou não
                messages.error(request, 'E-mail ou senha invalidos.')
    else:
        form = LoginForm()

    return render(request, 'auth/login.html', {'form': form})


def register(request):
    """
    Cadastro de novo usuário.

    Usa UserRegistrationForm (que estende UserCreationForm do Django),
    com campos adicionais médicos como CPF, tipo sanguíneo e alergias.

    Após o cadastro bem-sucedido, o usuário já é autenticado automaticamente
    (sem precisar fazer login manualmente).

    Fluxo:
        GET  → exibe o formulário de cadastro vazio
        POST → valida dados → salva → faz login automático → redireciona
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Login automático após o cadastro — melhora a experiência do usuário
            login(request, user)
            messages.success(request, 'Cadastro realizado com sucesso!')
            return redirect('home')
        else:
            # Exibe cada erro de validação como mensagem individual
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = UserRegistrationForm()

    return render(request, 'auth/register.html', {'form': form})


def logout_view(request):
    """
    Encerra a sessão do usuário.

    logout() remove a sessão do servidor e limpa o cookie do navegador.
    """
    logout(request)
    messages.success(request, 'Logout realizado com sucesso!')
    return redirect('home')


# ============================================================================
# VIEWS AUTENTICADAS — exigem @login_required
# ============================================================================

@login_required
def appointment_create(request):
    """
    Criação de agendamento em múltiplas etapas (tudo em uma única URL).

    O formulário funciona de forma progressiva via POST:
        Etapa 1 — usuário seleciona a especialidade
                  → view carrega os médicos daquela especialidade
        Etapa 2 — usuário seleciona o médico
                  → view mantém a seleção no contexto
        Etapa 3 — usuário seleciona a data
                  → DoctorService calcula os horários disponíveis
        Etapa 4 — usuário seleciona o horário e informa o motivo
        Confirmação — campo hidden 'confirm' presente
                  → AppointmentService valida e cria o agendamento

    Cada etapa é detectada pela presença dos campos no POST.
    Não há JavaScript — tudo é controlado pelo servidor.
    """
    specialties = Specialty.objects.all()
    today       = datetime.now().strftime('%Y-%m-%d')  # data mínima para o datepicker

    # Contexto inicial — campos None serão preenchidos conforme o usuário avança
    context = {
        'specialties':       specialties,
        'today':             today,
        'doctors':           None,
        'available_slots':   None,
        'selected_specialty':None,
        'selected_doctor':   None,
        'selected_date':     None,
    }

    if request.method == 'POST':
        specialty_id = request.POST.get('specialty')
        doctor_id    = request.POST.get('doctor')
        date_str     = request.POST.get('date')
        time_str     = request.POST.get('time')
        reason       = request.POST.get('reason')
        confirm      = request.POST.get('confirm')  # campo hidden no último passo

        # ── CONFIRMAÇÃO FINAL ────────────────────────────────────────────────
        # Todos os campos preenchidos + campo 'confirm' = criar o agendamento
        if confirm and specialty_id and doctor_id and date_str and time_str and reason:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            # Domingo (weekday == 6) não tem atendimento
            if appointment_date.weekday() == 6:
                messages.error(request, 'Nao e possivel agendar consultas aos domingos.')
                return redirect('appointment_create')

            # Delega a criação para o Service (validação de conflito de horário, etc.)
            appointment, error = AppointmentService.create(
                patient          = request.user,
                doctor_id        = doctor_id,
                specialty_id     = specialty_id,
                appointment_date = appointment_date,
                appointment_time = time_str,
                reason           = reason
            )

            if appointment:
                messages.success(request, 'Consulta agendada com sucesso!')
                return redirect('appointment_list')
            else:
                messages.error(request, error)
                return redirect('appointment_create')

        # ── ETAPA 1: especialidade selecionada → carrega médicos ─────────────
        if specialty_id:
            context['selected_specialty'] = int(specialty_id)
            context['doctors'] = DoctorService.get_by_specialty(specialty_id)

        # ── ETAPA 2: médico selecionado → mantém no contexto e carrega agenda ──
        if doctor_id:
            context['selected_doctor'] = int(doctor_id)
            # Carrega os dias/horários de atendimento do médico para exibir no form
            context['doctor_schedule'] = DoctorAvailability.objects.filter(
                doctor_id=doctor_id
            ).order_by('day_of_week')

        # ── ETAPA 3: data selecionada → calcula horários disponíveis ─────────
        if doctor_id and date_str:
            appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()

            if appointment_date.weekday() == 6:
                messages.warning(request, 'Nao atendemos aos domingos. Selecione outro dia.')
            else:
                context['selected_date']    = date_str
                context['available_slots']  = DoctorService.get_available_slots(doctor_id, date_str)

    return render(request, 'core/appointment_create.html', context)


@login_required
def appointment_list(request):
    """
    Lista todas as consultas do usuário autenticado.

    Filtra pelo patient=request.user para garantir que cada usuário
    veja apenas suas próprias consultas.

    select_related('doctor', 'specialty') evita o problema N+1:
    em vez de uma query por consulta para buscar médico e especialidade,
    o Django faz apenas 1 query com JOIN.
    """
    appointments = Appointment.objects.filter(
        patient=request.user
    ).select_related('doctor', 'specialty').order_by('-date', '-time')

    return render(request, 'core/appointment_list.html', {
        'appointments': appointments
    })


@login_required
@require_POST
def appointment_cancel(request, pk):
    """
    Cancela uma consulta do usuário autenticado.

    @require_POST garante que esta operação só acontece via formulário
    (não por acesso direto à URL via GET) — proteção básica contra CSRF
    em conjunto com o {% csrf_token %} no template.

    get_object_or_404 com patient=request.user garante que o usuário
    só pode cancelar suas próprias consultas (não as de outros pacientes).
    """
    # Valida que a consulta existe E pertence ao usuário logado
    get_object_or_404(Appointment, pk=pk, patient=request.user)

    success, message = AppointmentService.cancel(pk)
    if success:
        messages.success(request, message)
    else:
        messages.error(request, message)

    return redirect('appointment_list')


@login_required
def service_list(request):
    """
    Lista as especialidades disponíveis na clínica.

    Funciona como um catálogo de serviços — o usuário pode ver
    preços, duração e descrição de cada especialidade antes de agendar.
    """
    specialties = Specialty.objects.all()
    return render(request, 'core/service_list.html', {
        'specialties': specialties
    })
