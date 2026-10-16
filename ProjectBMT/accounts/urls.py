from django.urls import path
from . import views


urlpatterns = [

    # Authentication
    path(
        'login/',
        views.login_view,
        name='login'
    ),

    path(
        'logout/',
        views.logout_view,
        name='logout'
    ),


    # Dashboard
    path(
        '',
        views.dashboard_view,
        name='dashboard'
    ),


    # Employés
    path(
        'employes/',
        views.employee_list,
        name='employee_list'
    ),

    path(
        'employes/ajouter/',
        views.employee_create,
        name='employee_create'
    ),

    path(
        'employes/<int:employee_id>/modifier/',
        views.employee_update,
        name='employee_update'
    ),

    path(
        'employes/<int:employee_id>/activer-desactiver/',
        views.employee_toggle_active,
        name='employee_toggle_active'
    ),

]