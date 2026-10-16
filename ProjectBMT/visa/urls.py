from django.urls import path
from . import views

urlpatterns = [
    path('', views.visa_list, name='visa_list'),
    path('ajouter/', views.visa_create, name='visa_create'),
    path('<int:visa_id>/', views.visa_detail, name='visa_detail'),
    path(
        '<int:visa_id>/modifier/',
        views.visa_update,
        name='visa_update'
    ),
]