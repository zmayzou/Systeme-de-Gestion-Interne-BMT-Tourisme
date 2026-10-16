from django.urls import path
from . import views

urlpatterns = [
    path('', views.paiement_list, name='paiement_list'),
    path('ajouter/', views.paiement_create, name='paiement_create'),
    path('<int:paiement_id>/', views.paiement_detail, name='paiement_detail'),
    path(
        '<int:paiement_id>/modifier/',
        views.paiement_update,
        name='paiement_update'
    ),
]