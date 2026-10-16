from django.urls import path
from . import views

urlpatterns = [
    path('', views.dossier_list, name='dossier_list'),
    path('ajouter/', views.dossier_create, name='dossier_create'),
    path('<int:dossier_id>/', views.dossier_detail, name='dossier_detail'),
    path('<int:dossier_id>/modifier/', views.dossier_update, name='dossier_update'),
    path('<int:dossier_id>/documents/ajouter/',views.document_create,name='document_create'),
    path('documents/<int:document_id>/modifier/',views.document_update,name='document_update'),
    path('documents/<int:document_id>/supprimer/',views.document_delete,name='document_delete'),
]