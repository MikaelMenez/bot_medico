from django.contrib import admin
from whatsapp.models import Message, Paciente, Doctor

admin.site.register(Paciente)
admin.site.register(Message)
admin.site.register(Doctor)
