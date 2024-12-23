from django.urls import path, include
from . import views
from .views import pedir_hora, get_available_times

urlpatterns = [
  # vistas generales
  path('index', views.index, name='index'),
  path('administrar_datos', views.administrar_datos, name='administrar_datos'),
  path('perfil', views.perfil, name='perfil'),

  path('editar_perfil', views.editar_perfil, name='editar_perfil'),
  path('guardar_datos', views.guardar_datos, name='guardar_datos'),

  path('login', views.login, name='login'),
  path('logout', views.logout, name='logout'),
  path('validar', views.validar, name='validar'),

  path('registrarse', views.registrarse, name='registrarse'),
  path('registrar_usuario', views.registrar_usuario, name='registrar_usuario'),
  path('validar_token/', views.validar_token, name='validar_token'),
  path('reenviar_token/', views.reenviar_token, name='reenviar_token'),
  
  # vistas para paciente
  path('form_cita', views.form_cita, name='form_cita'),
  path('pedir_hora', pedir_hora, name='pedir_hora'),
  path('get_available_times/', get_available_times, name='get_available_times'),
  path('cancelar_hora', views.cancelar_hora, name='cancelar_hora'),
  #path('eliminar_hora/<str:id>', views.eliminar_hora, name='eliminar_hora'),

  # vistas para médicos
  path('index_medicos', views.index_medicos, name='index_medicos'),
  path('nuevo_anuncio', views.nuevo_anuncio, name='nuevo_anuncio'),
  path('guardar_anuncio', views.guardar_anuncio, name='guardar_anuncio'),

  path('eliminar_anuncio/<str:id>', views.eliminar_anuncio, name='eliminar_anuncio'),
  path('eliminar_hora/<str:id>', views.eliminar_hora, name='eliminar_hora'),
  path('eliminar_usuario/<str:rut>', views.eliminar_usuario, name='eliminar_usuario'),
]