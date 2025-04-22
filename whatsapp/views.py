from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from django.core.files.base import ContentFile
from whatsapp.models import Message, Paciente, Doctor
from datetime import date, datetime, timedelta
from django.utils import timezone
from twilio.rest import Client
import threading
import json
import requests

TWILIO_ACCOUNT_SID = settings.TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN = settings.TWILIO_AUTH_TOKEN
TWILIO_WHATSAPP_NUMBER = settings.TWILIO_WHATSAPP_NUMBER
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
ai_client = settings.CLIENT

#Classe responsavel por conectar e fazer as chamadas para a api do twilio
class WhatsappApi(APIView):
    @method_decorator(csrf_exempt)
    def post(self, request):
        sender = request.POST.get("From", "").replace("whatsapp:", "")
        text = request.POST.get("Body", "").lower()

        if text == 'encerrar':
            new_message = Message.objects.filter(sender=sender).order_by('-created_at').first()
            new_message.answer = text
            new_message.save()
            end_care(sender)
        else:
            numero_da_mensagem = Message.objects.filter(sender=sender, finished=False).count()

            if numero_da_mensagem == 0:
                try:
                    paciente = Paciente.objects.get(number=sender)
                except:
                    paciente = Paciente.objects.get(name='test_user')
                horario = datetime.now().strftime("%H:%M:%S")
                question = (
                    f"""O paciente {paciente.name}, possui {paciente.age} anos e realizou um(a) {paciente.procedure}.
                    Inicie uma conversa com ele, cumprimente-o de acordo com o horário atual {horario},
                    pergunte se ele está sentindo dores e avise que se ele quiser encerrar a consulta, basta digitar 'encerrar'.
                    Peça para que o paciente envie uma mensagem por vez."""
                )
                send_message(question, sender)
                paciente.in_care = True
                paciente.save()
            else:
                process_message(sender, text, numero_da_mensagem)
                threading.Timer(600, check_inactivity, args=[sender]).start()

        return Response({'message': 'Mensagem processada'}, status=200)

def process_message(sender, text, numero_da_mensagem):
    new_message = Message.objects.filter(sender=sender).order_by('-created_at').first()
    new_message.answer = text
    new_message.save()
    mensagens_anteriores = Message.objects.filter(sender=sender, finished=False)
    if numero_da_mensagem == 1:
        context = f'O usuário foi perguntado se está sentindo dor e respondeu {text}. Isso foi um "sim" ou um "não"?'
        response = ai_text(context)

        question = (
            "Que ótimo. Ficamos muito felizes com essa evolução. Diga 'encerrar' para terminar a consulta"
            if 'não' in response else
            "Em uma escala de 1( mínima dor ) - 10 ( máxima dor ), como o(a) Sr(a), classifica essa dor ?"
        )
    elif numero_da_mensagem == 2:
        context = f'O usuário foi perguntado o nível de dor em uma escala de 0 a 10 e respondeu {text}. Informe apenas o número, caso ele responda um valor fora da escala, diga "erro".'
        response = ai_text(context)
        if response in ["1", "2", "3"]:
            question = (
                "Compreendi! Dor leve está dentro de uma evolução esperada. "
                "Estamos comunicando a equipe dessa evolução. "
                "Por favor, mantenha todas as orientações fornecidas pelo seu médico. "
                "Digite 'Encerrar' para finalizar a consulta."
            )
        elif response in ["4", "5", "6", "7"]:
            question = "Entendi! O(a) Sr(a) tomou algum analgésico?"
        elif response in ["8", "9", "10"]:
            question = " Registrado ! Sr(a) ……, o seu médico / membro da equipe entrará em contato em instantes."
            end_care(sender)
        else:
            new_message.delete()
            question = "Por favor, informe apenas valores de 1 a 10."
    elif numero_da_mensagem == 3:
        question = "Essa dor está durando quanto tempo ? (A) até 6 horas de duração, (B) entre 6-12 horas de duração ou (C) mais de 12 horas de duração"
    elif numero_da_mensagem == 4:
        context = f'O usuário foi questionado e respondeu a seguinte numero {text}. Qual numero foi escolhido ? Responda apenas com o numero'
        response = int(ai_text(context))
        question = ("Poderia nos encaminhar uma foto do local da dor?" if response == 'A'or 'B' or 'a' or 'b' else "Registrado! O seu médico ou um membro da equipe entrará em contato em instantes.")
    else:
        question = "Digite 'Encerrar' para finalizar a consulta."
    mensagens_anteriores.update(read=True)
    send_message(question, sender, False)

# Encerra a consulta
def end_care(sender):
    try:
        paciente = Paciente.objects.get(number=sender)
    except:
        paciente = Paciente.objects.get(name='test_user')
    paciente.in_care = False
    paciente.save()
    send_resume(sender)

# Cria o resumo da conversa para o médico
def send_resume(sender):
    try:
        paciente = Paciente.objects.get(number=sender)
    except:
        paciente = Paciente.objects.get(name='test_user')
    conversas = Message.objects.filter(sender=sender, question__isnull=False, finished=False).exclude(question="")
    historico = list(map(lambda message: {'question':message.question, 'answer':message.answer}, conversas))
    context = f'O paciente {paciente.name}, possui {paciente.age} anos e realizou um(a) {paciente.procedure} na data {paciente.procedure_date} e teve a seguinte conversa na data {date.today()}:'
    context += ' '.join(map(lambda conversa: f"pergunta: {conversa['question']} resposta: {conversa['answer']}", historico))
    context += "faça um resumo apenas com informações uteis sobre a dor relatada pelo paciente em topicos curtos, não precisa adicionar a conversa em si ou contatos caso tenha no resumo.Quando uma informação for urgente ou extremamente importante, sinalize isto colocando a frase dentro de dois asteriscos,assim por exemplo : *Paciente sente dor nivel 10*"
    conversas.update(finished=True)
    send_message(context, paciente.doctor.number)


# Função responsável por enviar as messagens
def send_message(context, number, openai=True):
    if openai:
        message = ai_text(context)
    else:
        message = context
    Message.objects.create(question=message, sender=number)
    message = client.messages.create(
        from_=f'whatsapp:{TWILIO_WHATSAPP_NUMBER}',
        body=message,
        to=f'whatsapp:{number}'
    )

# Caso o usuário passe mais de 10 minutos sem enviar uma mensagem, envia um alerta para que ele encerre.
def check_inactivity(sender):
    doctor = Doctor.objects.filter(number=sender).exists()
    if doctor:
        return
    last_message = Message.objects.filter(sender=sender).order_by('-created_at').first()
    if last_message.answer:
        if 'encerrar' in last_message.answer:
            return
    delta_time = timezone.now() - last_message.created_at
    if delta_time > timedelta(minutes=1):
            message = 'Por favor digite "encerrar" para finalizar a conversa'
            send_message(message, sender, False)

def ai_text(context):
    completion = ai_client.chat.completions.create(
            messages=[
            {"role": "system", "content": context},
            ],model="gpt-4o-mini")

    return completion.choices[0].message.content
