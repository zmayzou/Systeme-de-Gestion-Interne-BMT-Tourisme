from django.contrib import admin
from .models import Role, PermissionMetier, Employe

admin.site.register(Role)
admin.site.register(PermissionMetier)
admin.site.register(Employe)