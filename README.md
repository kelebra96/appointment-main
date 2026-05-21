# AgendaMed - Sistema de Agendamento de Consultas

Sistema de agendamento de consultas medicas desenvolvido em Python/Django.

Telas/prototipo: https://www.figma.com/proto/S70Dru6oC1RnucpDT9rbi6/Sem-t%C3%ADtulo?node-id=0-1&t=jfvWl4ZEoboxgCFY-1

## Objetivo do Projeto

Projeto final da disciplina de Programacao Web, seguindo a alternativa fullstack
com Django SSR. O sistema permite cadastro e autenticacao de pacientes,
gerenciamento administrativo de especialidades e medicos, controle de agenda e
agendamento de consultas.

## Requisitos

- Python 3.10+
- pip

## Instalacao

1. Criar ambiente virtual:
```bash
python -m venv .venv
```

2. Ativar ambiente virtual:
```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

3. Instalar dependencias:
```bash
pip install -r requirements.txt
```

4. Configurar variaveis de ambiente:
```bash
cp .env.example .env
# Editar .env com suas configuracoes
```

5. Executar migracoes:
```bash
python manage.py migrate
```

6. Carregar dados iniciais para apresentacao:
```bash
python manage.py loaddata initial_data
```

7. Criar superusuario (admin):
```bash
python manage.py createsuperuser
```

8. Executar servidor:
```bash
python manage.py runserver
```

9. Acessar aplicacao:
- Sistema: http://localhost:8000
- Admin Django: http://localhost:8000/admin/

## Funcionalidades

### Usuarios
- Cadastro de pacientes
- Login/Logout
- Recuperacao de senha por e-mail
- Perfil com informacoes medicas (tipo sanguineo, alergias, convenio)

### Consultas
- Agendamento de consultas em etapas
- Visualizacao de consultas agendadas
- Cancelamento de consultas
- Selecao de medico por especialidade
- Selecao de horarios disponiveis

### Administracao
- Gerenciamento de especialidades (CRUD)
- Gerenciamento de medicos (CRUD)
- Gerenciamento de consultas
- Calendario de agendamentos
- Django Admin para gerenciamento avancado

## Estrutura do Projeto

```
agendamed/
├── agendamed/          # Configuracoes do projeto Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── core/               # App principal
│   ├── admin.py        # Configuracao do Django Admin
│   ├── forms.py        # Formularios
│   ├── models.py       # Modelos de dados
│   ├── services.py     # Logica de negocio
│   ├── templatetags/   # Template tags customizadas
│   ├── urls.py         # Rotas
│   └── views.py        # Views/Controllers
├── templates/          # Templates HTML
│   ├── auth/           # Templates de autenticacao
│   ├── core/           # Templates principais
│   └── partials/       # Componentes reutilizaveis
├── static/             # Arquivos estaticos
│   ├── css/            # Estilos CSS
│   └── images/         # Imagens
├── manage.py
└── requirements.txt
```

## Modelos de Dados

- **User**: Usuario do sistema (paciente ou admin)
- **Specialty**: Especialidade medica
- **Doctor**: Medico
- **DoctorAvailability**: Disponibilidade do medico
- **Appointment**: Consulta agendada

## Entrega Final

- Alternativa escolhida: Fullstack Django (SSR)
- ORM/Admin: models e Django Admin configurados para usuarios, especialidades,
  medicos, disponibilidades e consultas
- CRUD: gerenciamento de especialidades, medicos e agendamentos
- Autenticacao: cadastro, login, logout e recuperacao de senha
- Fixtures: `core/fixtures/initial_data.json`

## Tecnologias

- Python 3.10+
- Django 5.0+
- SQLite (banco de dados)
- Bootstrap 5 (CSS via CDN)
- Django Templates (sem JavaScript)
