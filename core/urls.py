"""
urls.py — Mapeamento de URLs da aplicação AgendaMed

Este arquivo conecta cada URL a uma view. Quando o usuário acessa um endereço,
o Django percorre essa lista em ordem e chama a view da primeira URL que casar.

Como funciona o roteamento no Django:
    1. O Django lê o agendamed/urls.py (raiz do projeto)
    2. Que inclui este arquivo com: path('', include('core.urls'))
    3. Aqui cada path() associa uma URL a uma função de view

Parâmetros de URL:
    <int:pk> → captura um número inteiro e passa como argumento pk para a view
               Ex: /appointment/42/cancel/ → appointment_cancel(request, pk=42)

Estrutura das rotas:
    Públicas    → home, login, logout, register
    Autenticadas → appointment/*, services/
"""

from django.urls import path
from . import views

urlpatterns = [
    # ── ROTAS PÚBLICAS ────────────────────────────────────────────────────────
    # Qualquer visitante pode acessar, logado ou não

    path('', views.home, name='home'),
    # name='home' permite usar {% url 'home' %} nos templates
    # e redirect('home') nas views — sem hardcodar a URL

    path('login/',    views.login_view,   name='login'),
    path('logout/',   views.logout_view,  name='logout'),
    path('register/', views.register,     name='register'),

    # ── ROTAS AUTENTICADAS ────────────────────────────────────────────────────
    # Exigem @login_required na view — redireciona para /login/ se não logado

    path('appointment/create/',              views.appointment_create, name='appointment_create'),
    path('appointment/',                     views.appointment_list,   name='appointment_list'),
    path('appointment/<int:pk>/cancel/',     views.appointment_cancel, name='appointment_cancel'),
    # <int:pk> captura o ID da consulta na URL e envia para a view

    path('services/', views.service_list, name='service_list'),
]
