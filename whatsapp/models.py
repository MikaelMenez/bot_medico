from django.db import models

class Doctor(models.Model):
    name = models.CharField(max_length=120)
    number = models.CharField(max_length=14)

class Paciente(models.Model):
    GENDERS = {
        "M":"Masculino",
        "F":"Feminino",
        "NA":"Prefiro não informar",
    }
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='pacientes')
    name = models.CharField(max_length=150)
    age = models.IntegerField()
    number = models.CharField(max_length=14, null=True, blank=True)
    gender = models.CharField(max_length=150, choices=GENDERS)
    procedure = models.CharField(max_length=150)
    procedure_date = models.DateField(auto_now_add=True)
    in_care = models.BooleanField(default=False)

class Message(models.Model):
    question = models.CharField(max_length=500, blank=True, null=True)
    answer = models.CharField(max_length=500, blank=True, null=True)
    sender = models.CharField(max_length=120, blank=True, null=True)
    read = models.BooleanField(default=False)
    finished = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

# Arquivo que vai cadastrar os pacientes
class File(models.Model):
    file = models.FileField(upload_to="pacientes/")
    created_at = models.DateTimeField(auto_now_add=True)
    def __str__(self):
        return f"{self.file}"
