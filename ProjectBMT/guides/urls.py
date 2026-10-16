from django.urls import path
from . import views

urlpatterns = [
    path('', views.mission_list, name='mission_list'),
    path('ajouter/', views.mission_create, name='mission_create'),
    path('<int:mission_id>/',views.mission_detail,name='mission_detail'),
    path('<int:mission_id>/modifier/',views.mission_update,name='mission_update'),
    path('guides/', views.guide_list, name='guide_list'),
    path('guides/ajouter/', views.guide_create, name='guide_create'),
    path('<int:mission_id>/statut/',views.mission_update_status,name='mission_update_status'),
]