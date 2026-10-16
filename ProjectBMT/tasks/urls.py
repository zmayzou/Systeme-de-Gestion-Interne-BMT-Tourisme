from django.urls import path
from . import views

urlpatterns = [
    path('', views.task_list, name='task_list'),

    path(
        'ajouter/',
        views.task_create,
        name='task_create'
    ),

    path(
        '<int:task_id>/',
        views.task_detail,
        name='task_detail'
    ),

    path(
        '<int:task_id>/modifier/',
        views.task_update,
        name='task_update'
    ),
]