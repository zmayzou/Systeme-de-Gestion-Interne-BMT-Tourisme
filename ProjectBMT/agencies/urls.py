from django.contrib import admin
from django.urls import path, include


urlpatterns = [

    path('admin/', admin.site.urls),

    path('', include('accounts.urls')),

    path('agences/', include('agencies.urls')),

    path('clients/', include('clients.urls')),

    path('dossiers/', include('dossiers.urls')),

    path('tasks/', include('tasks.urls')),

    path('paiements/', include('payments.urls')),

    path('visas/', include('visa.urls')),

    path('billetterie/', include('ticketing.urls')),

    path('missions/', include('guides.urls')),

]