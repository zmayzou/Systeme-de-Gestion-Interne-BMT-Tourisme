from django.urls import path
from . import views

urlpatterns = [
    path('', views.billet_list, name='billet_list'),
    path('ajouter/', views.billet_create, name='billet_create'),
    path('<int:billet_id>/', views.billet_detail, name='billet_detail'),
    path(
        '<int:billet_id>/modifier/',
        views.billet_update,
        name='billet_update'
    ),
]