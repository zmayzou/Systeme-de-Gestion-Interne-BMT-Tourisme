from django.urls import path
from . import views


urlpatterns = [

    path(
        '',
        views.notification_list,
        name='notification_list'
    ),

    path(
        '<int:notification_id>/lue/',
        views.notification_mark_read,
        name='notification_mark_read'
    ),

    path(
        'tout-lire/',
        views.notification_mark_all_read,
        name='notification_mark_all_read'
    ),

    path(
        '<int:notification_id>/supprimer/',
        views.notification_delete,
        name='notification_delete'
    ),

    path(
        'historique/',
        views.historique_list,
        name='historique_list'
    ),

]