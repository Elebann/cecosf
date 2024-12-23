# sendgrid for mail feature
import os
import ssl
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
# token generator
import secrets

# disable ssl for sendgrid (local purposes).
if (not os.environ.get('PYTHONHTTPSVERIFY', '') and
    getattr(ssl, '_create_unverified_context', None)):
    ssl._create_default_https_context = ssl._create_unverified_context

# con esta funcion enviamos mails.
def sendmail(destiny, subject, template_name, context):
    html_content = render_to_string(template_name, context)
    text_content = strip_tags(html_content)

    message = (
        Mail(
            from_email='',
            to_emails=destiny,
            subject=subject,
            html_content=html_content,
            plain_text_content=text_content
        )
    )

    try:
        sg = SendGridAPIClient(api_key=os.getenv("SG_APIKEY"))
        response = sg.send(message)
        print(response.status_code)
        print(response.body)
        print(response.headers)
    except Exception as e:
        print(e)

def sendMailBienvenida(correo, nombre, url_validar):
    subject = "Bienvenido al Cecosf Atacama"
    template_name = 'emails/nueva_cuenta.html'
    context = {'nombre': nombre, 'url_validar': url_validar}
    sendmail(correo, subject, template_name, context)

def sendMailValidar(correo, nombre, url_validar):
    subject = "Valida tu cuenta"
    template_name = 'emails/validar_cuenta.html'
    context = {'nombre': nombre, 'url_validar': url_validar}
    sendmail(correo, subject, template_name, context)

def sendMailHoraRegistrada(correo, nombre, doctor, fecha, hora, razon):
    subject = "Hora registrada"
    template_name = 'emails/hora_registrada.html'
    context = {'nombre': nombre, 'doctor': doctor, 'fecha': fecha, 'hora': hora, 'razon': razon}
    sendmail(correo, subject, template_name, context)

def generar_token():
    return secrets.token_urlsafe(50)