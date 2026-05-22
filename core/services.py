"""
services.py — Camada de lógica de negócio do AgendaMed

Por que ter uma camada de Services separada das Views?

No padrão Django simples, a lógica fica nas views. Mas quando essa lógica
cresce (validações complexas, cálculos, múltiplas queries), as views ficam
difíceis de ler e testar.

A solução é mover a lógica para classes de Service:
    - View        → "o que mostrar e para onde redirecionar"
    - Service     → "como criar, validar e manipular os dados"

Classes neste arquivo:
    AppointmentService  → criar, verificar disponibilidade e cancelar consultas
    DoctorService       → buscar médicos e calcular horários disponíveis
"""

from datetime import datetime, timedelta, date
from .models import Appointment, Doctor, DoctorAvailability


class AppointmentService:
    """Operações de negócio relacionadas a agendamentos."""

    @staticmethod
    def create(patient, doctor_id, specialty_id, appointment_date, appointment_time, reason):
        """
        Cria um novo agendamento com todas as validações necessárias.

        Responsabilidades:
            1. Verifica se o médico existe e está ativo
            2. Converte a string de horário para objeto time do Python
            3. Calcula o horário de término baseado na duração da especialidade
            4. Verifica se o slot está disponível (não há conflito de horário)
            5. Cria o registro no banco de dados

        Args:
            patient          : instância do User (paciente logado)
            doctor_id        : ID do médico selecionado
            specialty_id     : ID da especialidade selecionada
            appointment_date : objeto date (data da consulta)
            appointment_time : string no formato 'HH:MM'
            reason           : string com o motivo da consulta

        Returns:
            (appointment, None)   → sucesso: retorna o objeto criado
            (None, 'mensagem')    → falha: retorna None + descrição do erro
        """
        try:
            doctor = Doctor.objects.get(pk=doctor_id, is_active=True)
        except Doctor.DoesNotExist:
            return None, 'Médico não encontrado ou inativo.'

        # Converte string 'HH:MM' para objeto time — necessário para o banco
        if isinstance(appointment_time, str):
            time_obj = datetime.strptime(appointment_time, '%H:%M').time()
        else:
            time_obj = appointment_time

        # Calcula horário de término: combina data+hora em datetime, soma duração,
        # extrai só o horário. Ex: 14:00 + 30min = 14:30
        duration        = doctor.specialty.duration
        start_datetime  = datetime.combine(appointment_date, time_obj)
        end_datetime    = start_datetime + timedelta(minutes=duration)
        time_end        = end_datetime.time()

        # Checa conflito antes de criar (evita dois pacientes no mesmo horário)
        if not AppointmentService.is_slot_available(doctor_id, appointment_date, appointment_time):
            return None, 'Este horário não está mais disponível.'

        appointment = Appointment.objects.create(
            patient     = patient,
            doctor      = doctor,
            specialty_id= specialty_id,
            date        = appointment_date,
            time        = time_obj,
            time_end    = time_end,
            reason      = reason,
            status      = 'agendado'
        )

        return appointment, None

    @staticmethod
    def is_slot_available(doctor_id, appointment_date, appointment_time):
        """
        Verifica se um horário específico está disponível para um médico.

        Retorna False se já existir uma consulta 'agendada' ou 'confirmada'
        para o mesmo médico, data e horário.

        Consultas 'canceladas' e 'realizadas' não bloqueiam o horário,
        permitindo reaproveitar slots liberados.
        """
        if isinstance(appointment_time, str):
            time_obj = datetime.strptime(appointment_time, '%H:%M').time()
        else:
            time_obj = appointment_time

        already_booked = Appointment.objects.filter(
            doctor_id   = doctor_id,
            date        = appointment_date,
            time        = time_obj,
            status__in  = ['agendado', 'confirmado']  # só bloqueia consultas ativas
        ).exists()

        return not already_booked

    @staticmethod
    def update(appointment_id, doctor_id, specialty_id, appointment_date, appointment_time, reason):
        try:
            appointment = Appointment.objects.get(pk=appointment_id)
        except Appointment.DoesNotExist:
            return None, 'Consulta não encontrada.'

        if appointment.status not in ['agendado', 'confirmado']:
            return None, 'Esta consulta não pode ser editada.'

        try:
            doctor = Doctor.objects.get(pk=doctor_id, is_active=True)
        except Doctor.DoesNotExist:
            return None, 'Médico não encontrado ou inativo.'

        if isinstance(appointment_time, str):
            time_obj = datetime.strptime(appointment_time, '%H:%M').time()
        else:
            time_obj = appointment_time

        duration       = doctor.specialty.duration
        start_datetime = datetime.combine(appointment_date, time_obj)
        time_end       = (start_datetime + timedelta(minutes=duration)).time()

        already_booked = Appointment.objects.filter(
            doctor_id  = doctor_id,
            date       = appointment_date,
            time       = time_obj,
            status__in = ['agendado', 'confirmado']
        ).exclude(pk=appointment_id).exists()

        if already_booked:
            return None, 'Este horário não está mais disponível.'

        appointment.doctor_id    = doctor_id
        appointment.specialty_id = specialty_id
        appointment.date         = appointment_date
        appointment.time         = time_obj
        appointment.time_end     = time_end
        appointment.reason       = reason
        appointment.save()

        return appointment, None

    @staticmethod
    def cancel(appointment_id):
        """
        Cancela uma consulta alterando seu status para 'cancelado'.

        Não deleta o registro — manter o histórico é importante.

        Returns:
            (True,  'mensagem de sucesso')
            (False, 'mensagem de erro')
        """
        try:
            appointment = Appointment.objects.get(pk=appointment_id)

            if appointment.status in ['agendado', 'confirmado']:
                appointment.status = 'cancelado'
                appointment.save()
                return True, 'Consulta cancelada com sucesso.'

            # Consulta já realizada ou já cancelada não pode ser cancelada novamente
            return False, 'Esta consulta não pode ser cancelada.'

        except Appointment.DoesNotExist:
            return False, 'Consulta não encontrada.'


class DoctorService:
    """Operações de negócio relacionadas a médicos."""

    @staticmethod
    def get_available_slots(doctor_id, appointment_date, exclude_appointment_id=None):
        """
        Retorna a lista de horários disponíveis para um médico em uma data.

        Algoritmo:
            1. Busca os registros de DoctorAvailability para o dia da semana
            2. Para cada bloco de disponibilidade, gera slots com intervalo
               igual à duração da especialidade (ex: a cada 30 minutos)
            3. Remove os horários já ocupados por consultas ativas
            4. Se a data for hoje, remove também os horários que já passaram

        Detalhe importante — conversão de dia da semana:
            Python:          segunda=0, terça=1, ..., domingo=6
            Nosso modelo:    domingo=0, segunda=1, ..., sábado=6
            Conversão:       js_weekday = (python_weekday + 1) % 7

        Args:
            doctor_id        : ID do médico
            appointment_date : string 'YYYY-MM-DD' ou objeto date

        Returns:
            list[str] — lista de horários no formato 'HH:MM', ordenados
        """
        try:
            doctor = Doctor.objects.get(pk=doctor_id, is_active=True)
        except Doctor.DoesNotExist:
            return []

        # Garante que appointment_date é um objeto date
        if isinstance(appointment_date, str):
            appointment_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()

        # Converte o dia da semana do Python para o formato do nosso modelo
        python_weekday = appointment_date.weekday()
        js_weekday     = (python_weekday + 1) % 7

        # Busca os blocos de disponibilidade do médico nesse dia
        availabilities = DoctorAvailability.objects.filter(
            doctor      = doctor,
            day_of_week = js_weekday
        )

        # Médico não trabalha neste dia da semana
        if not availabilities.exists():
            return []

        duration = doctor.specialty.duration  # minutos por consulta

        # Busca horários já ocupados para remover da lista
        qs = Appointment.objects.filter(
            doctor = doctor,
            date   = appointment_date,
            status__in = ['agendado', 'confirmado']
        )
        if exclude_appointment_id:
            qs = qs.exclude(pk=exclude_appointment_id)
        existing_appointments = qs.values_list('time', flat=True)

        booked_times = set(t.strftime('%H:%M') for t in existing_appointments)

        available_slots = []

        for availability in availabilities:
            # Gera slots do início ao fim da disponibilidade
            current = datetime.combine(appointment_date, availability.start_time)
            end     = datetime.combine(appointment_date, availability.end_time)

            # Avança de `duration` em `duration` minutos até o fim do bloco
            while current + timedelta(minutes=duration) <= end:
                slot_str = current.strftime('%H:%M')

                if slot_str not in booked_times:
                    if appointment_date == date.today():
                        # Para hoje: só mostra horários que ainda não passaram
                        if current.time() > datetime.now().time():
                            available_slots.append(slot_str)
                    else:
                        available_slots.append(slot_str)

                current += timedelta(minutes=duration)

        return sorted(available_slots)

    @staticmethod
    def get_by_specialty(specialty_id):
        """
        Retorna os médicos ativos de uma especialidade.

        Usado no formulário de agendamento para popular o select de médicos
        após o usuário escolher a especialidade.
        """
        return Doctor.objects.filter(
            specialty_id = specialty_id,
            is_active    = True
        ).order_by('name')
