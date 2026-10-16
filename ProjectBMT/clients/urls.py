from django.urls import path
from . import views

urlpatterns = [
    path('', views.client_list, name='client_list'),
    path('ajouter/', views.client_create, name='client_create'),
    path('<int:client_id>/modifier/', views.client_update, name='client_update'),
    path('<int:client_id>/supprimer/', views.client_delete, name='client_delete'),
]