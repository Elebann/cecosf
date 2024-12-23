# for send messages between pages
from django.contrib import messages
# for the ajax for available hours
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.db import IntegrityError, connection
from datetime import datetime, timedelta
from django.utils import timezone
from django.utils.timezone import make_aware
# for password hashing
import hashlib
# import sendgrid utility and random token generator
from .utils import sendMailBienvenida, sendMailValidar, sendMailHoraRegistrada, generar_token


# ---------------------- SETTINGS ----------------------

# redirect at the beginning
def go_to_index(request):
    return redirect('/cecosf/index')

# just in case, easy change of domain, used generally for mail options
sitio = 'http://127.0.0.1:8000/cecosf'

# ---------------------- VIEWS.PY ----------------------

# landing
def index(request):
    # check news
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM anuncios_recientes;")
        anuncios = cursor.fetchall()

        # prepare news in a list
        anuncios_list = [
            {
                "titulo": anuncio[1],
                "contenido": anuncio[2],
                "fecha": anuncio[3]
            }
            for anuncio in anuncios
        ]

    # if there are not a session. we sent this empty
    user_data = {}
    # validate if there are already a session
    try:
        # if so, we make the context
        rut = request.session.get('rut')
        nombre = request.session.get('nombre')
        apellido = request.session.get('apellido')
        medico = request.session.get('medico')
        validado = request.session.get('validado')

        print("index: sesión encontrada: " + nombre + " " + rut + " " + str(medico) + " " + str(validado))

        user_data = {
            'rut': rut,
            'nombre': nombre,
            'apellido': apellido,
            'medico': medico,
            'validado': validado
        }
    except:
        # if there aint an active session. dont do anything
        print("index: sin sesión activa.")

    context = {"anuncios": anuncios_list, "usuario": user_data}
    return render(request, 'cecosf/index.html', context)

# load the login html
def login(request):
    # check session first
    if request.session.get('rut'):
        rut = request.session.get('rut')
        nombre = request.session.get('nombre')
        cargo = request.session.get('cargo')
        print("login: sesión encontrada: " + nombre + " " + rut)

        # if the user is a doctor, redirect to doctor index
        if cargo == 2:
            return redirect('index_medicos')
        # if not, just load everyone's index
        return redirect('index')

    # if not session, load index
    context = {}
    return render(request, 'cecosf/login.html', context)

# take the data from the login
def validar(request):
    print("validar: validando el login")

    if request.method == "POST":
        # get form data
        rut = request.POST['rut']
        contrasena = request.POST['pass']

        # check if rut isnt text
        if not rut.isdigit():
            print("validar: RUT no es un número.")
            messages.error(request, "El RUT ingresado no es válido.")
            return redirect('login')

        if not contrasena:
            messages.error(request, "Debes rellenar todos los campos.")
            return redirect('login')

        # search for user in the DB
        with connection.cursor() as cursor:
            #with this stored procedure, we get the password (in hash)
            cursor.callproc('sp_obtenerContrasena', [rut])
            hash_almacenado = cursor.fetchone()

            if hash_almacenado is None:
                messages.error(request, "Usuario o contraseña incorrectos")
                return redirect('login')

        # make a hash with the password send by the user in the form, then compare the hashes
        contrasena_hash = hashlib.sha256(contrasena.encode()).hexdigest()

        if contrasena_hash == hash_almacenado[0]:
            print("validar: Contraseña correcta")

            with connection.cursor() as cursor:
                # with this SP, we get the user data
                cursor.callproc('sp_obtenerDatosUsuario', [rut])
                usuario = cursor.fetchone()

                if usuario:
                    print("validar: Usuario encontrado")

                    # create a django session
                    request.session['rut'] = rut
                    request.session['nombre'] = usuario[1]
                    request.session['apellido'] = usuario[2]
                    request.session['correo'] = usuario[3]
                    request.session['medico'] = usuario[5]
                    request.session['validado'] = usuario[6]

                    # redirect to doctor index if user is doctor
                    if usuario[5] == 1:
                        print("Usuario es médico")
                        return redirect('index_medicos')
                    else:
                        return redirect('index')

                # if the user has no coincidence, reload the login
                else:
                    print("Usuario no encontrado")
                    messages.error(request, "Usuario o contraseña incorrectos")
                    return redirect('login')
        else:
            print("Contraseña incorrecta")
            messages.error(request, "Usuario o contraseña incorrectos")
            return redirect('login')
    else:
        print("validar: Parece que no puedes hacer eso.")
        return redirect('index')

# just log out the user
def logout(request):
    request.session.flush()
    messages.success(request, "La sesión se ha cerrado.")
    return redirect('index')

# load register html
def registrarse(request):
    # si el usuario es médico podemos habilitar la opción de crearle una cuenta de médico a otro usuario
    if request.session.get('rut'):
        rut = request.session.get('rut')
        nombre = request.session.get('nombre')
        medico = request.session.get('medico')
        # guardar los datos de la sesión en un diccionario
        usuario_data = {'rut': rut, 'nombre': nombre, 'medico': medico}
        # para enviarlo en el contexto
        context = {'usuario': usuario_data}
        return render(request, 'cecosf/registrarse.html', context)

    # si no es médico, solo cargamos la página sin hacer nada más
    return render(request, 'cecosf/registrarse.html')

# logic for new users
def registrar_usuario(request):
    # get the rut first to check if the rut exists or doesnt exist
    rut = request.POST.get('rut')

    # check if the rut is not text
    if not rut.isdigit():
        print("registrar_usuario: RUT no es un número.")
        messages.error(request, "El RUT ingresado no es válido.")
        return redirect('registrarse')

    # validate if the user already exists
    with connection.cursor() as cursor:
        cursor.callproc('sp_verUsuario', [rut])
        usuario = cursor.fetchone()

        if usuario:
            messages.error(request, 'Ya existe un usuario con ese RUT.')
            return redirect('registrarse')

    # if not, proceed
    nombre = request.POST.get('nombre').capitalize()
    apellido = request.POST.get('apellido').capitalize()
    correo = request.POST.get('correo')
    contrasena = request.POST.get('contrasena')
    medico = request.POST.get('medico')
    # generate token
    token = generar_token()

    # change checkbox format
    if medico == "on":
        medico = 1
    else:
        medico = 0

    # protect the password, and save the hash
    contrasena = hashlib.sha256(contrasena.encode()).hexdigest()
    print("registrar_usuario: Contraseña encriptada: " + contrasena)

    # save principal data
    with connection.cursor() as cursor:
        try:
            cursor.callproc('sp_insertarUsuario', [rut, nombre, apellido, correo, contrasena, medico])
            print("registrar_usuario: Usuario insertado correctamente")

            # save the token for later validation
            cursor.callproc('sp_insertarToken', [rut, token])

        except IntegrityError as e:
            print("registrar_usuario: Error al insertar al nuevo usuario: " + str(e))
            return

    # get optional user data
    edad = request.POST.get('edad')
    telefono = request.POST.get('telefono')
    numhijos = request.POST.get('hijos')
    direccion = request.POST.get('direccion')

    # convert to none, the empty inputs
    if not edad:
        edad = None
    if not numhijos:
        numhijos = None
    if not telefono:
        telefono = None
    if not direccion:
        direccion = None

    # save the optional data
    with connection.cursor() as cursor:
        try:
            cursor.callproc('sp_insertarUsuarioDetalles', [rut, telefono, edad, numhijos, direccion])
            print("registrar_usuario: Detalles del usuario insertados correctamente")
        except IntegrityError as e:
            print("registrar_usuario: Error al insertar los detalles del usuario en la base de datos: " + str(e))

    # success message and redirect to login
    messages.success(request, 'Usuario registrado con éxito. Inicie sesión para continuar.')
    url_validar = (f'{sitio}/validar_token?token={token}')
    # send the welcome mail (this send the link to validate the account, with the token generated previously)
    sendMailBienvenida(correo, nombre, url_validar)
    return redirect('index')

def validar_token(request):
    token = request.GET.get('token', '')
    if token:
        with connection.cursor() as cursor:
            cursor.callproc('sp_buscarToken', [token])
            result = cursor.fetchone()

        if result and not result[1]:  # result[1] is 'usado'
            fecha_creacion = result[2]  # result[2] is 'fecha_creacion'
            if fecha_creacion.tzinfo is None:  # Check if fecha_creacion is naive
                fecha_creacion = make_aware(fecha_creacion)
            if timezone.now() < fecha_creacion + timedelta(minutes=15):
                with connection.cursor() as cursor:
                    cursor.callproc('sp_validarUsuarioYToken', [result[0], token])
                    return HttpResponse("Cuenta validada con éxito.")
            else:
                return HttpResponse("El token ha caducado. Puede generar uno nuevo en la sección 'Mi perfil' al iniciar sesión.")
        else:
            return HttpResponse("Token inválido o ya utilizado.")
    else:
        return HttpResponse("No se ha recibido un token.")

def reenviar_token(request):
    rut = request.session.get('rut', '')
    correo = request.session.get('correo', '')

    if rut and correo:
        with connection.cursor() as cursor:
            # check if user exists and get the rut
            cursor.execute("SELECT rut FROM usuario WHERE rut = %s AND correo = %s", (rut, correo))
            user = cursor.fetchone()
            if user:
                # delete previous token
                cursor.execute("DELETE FROM validacion_token WHERE rut_usuario = %s", (rut,))

                # generate a new one
                nuevo_token = generar_token()

                #insert the new token into db
                cursor.execute("INSERT INTO validacion_token (rut_usuario, token, fecha_creacion) VALUES (%s, %s, %s)",
                               (rut, nuevo_token, timezone.now()))

                # send the new token to user mail
                url_validar = f'{sitio}/validar_token?token={nuevo_token}'
                sendMailValidar(correo, request.session.get('nombre'), url_validar)

                return HttpResponse("Se ha enviado un nuevo token de validación a tu correo electrónico. <a href='/cecosf/index'>Volver al inicio</a>")
            else:
                return HttpResponse("No se encontró una cuenta con ese RUT y correo electrónico.")
    else:
        return HttpResponse("No se ha recibido un RUT o correo electrónico.")

# load the form to schedule an appointment
def form_cita(request):
    # check session
    try:
        rut = request.session.get('rut')
        nombre = request.session.get('nombre')
        validado = request.session.get('validado')

        if validado == 0:
            # if user hasnt validate the account, redirect and say validate is needed
            messages.error(request, 'Debes validar tu cuenta antes de pedir una hora.')
            return redirect('index')

        print("form_cita: sesión activa: " + nombre + " " + rut)
        user_data = {'rut': rut, 'nombre': nombre}

    except Exception as e:
        print("form_cita: sin sesión activa.")
        return redirect('login')

    # if a session is active, load doctors
    with connection.cursor() as cursor:
        try:
            # 'medicos' is a view, and we use it to make a select
            cursor.execute("SELECT * from medicos;")
            # store all the doctors
            medicos = cursor.fetchall()

            # split doctor data
            medicos_list = [
                {
                    "rut": medico[0],
                    "nombre": medico[1],
                }
                # make the dict for each doctor found
                for medico in medicos
            ]

            # send the data from user session and doctors
            context = {"medicos": medicos_list, "usuario": user_data}

        except IntegrityError as e:
            print("form_cita: error al consultar médicos: " + str(e))

    return render(request, 'cecosf/form_cita.html', context)

# with this AJAX function, we get the available hours for each doctor in a specific day
def get_available_times(request):
    # get doctor rut and date
    doctor_rut = request.GET.get('doctor_rut')
    fecha = request.GET.get('fecha')

    # available hours
    horarios = [
        '08:00', '09:00', '10:00', '11:00', '12:00',
        '13:00', '14:00', '15:00', '16:00', '17:00'
    ]

    # with both data, look for disponibility
    if doctor_rut and fecha:
        with connection.cursor() as cursor:
            cursor.callproc('sp_horasDisponibles', [doctor_rut, fecha])

            # get all the appointments made to that doctor on the selected day
            citas = cursor.fetchall()
            # extract the hours from the appointments
            ocupadas = [hora[0] for hora in citas]
            # prepare the available hours, deleting the hours already taken from the list above
            disponibles = [hora for hora in horarios if hora not in ocupadas]

            # send the available hours with json format
            return JsonResponse(disponibles, safe=False)

    # send available hours with json format
    return JsonResponse(horarios, safe=False)

# this function schedule the appointment
def pedir_hora(request):
    if request.method == 'POST':
        # get form data
        rut_paciente = request.POST.get('rut')
        rut_doctor = request.POST.get('doctor')
        fecha = request.POST.get('fecha')
        hora = request.POST.get('hora')
        razon = request.POST.get('razon')

        # check if all the form was completed
        if hora == None or fecha == None or razon == None or rut_doctor == None or rut_paciente == None:
            messages.error(request, 'Debes rellenar el formulario en su totalidad.')
            return redirect('form_cita')

        # check if the selected hours and date are available
        with connection.cursor() as cursor:
            cursor.callproc('sp_verificarDisponibilidad', [rut_doctor, fecha, hora])
            result = cursor.fetchone()

        # if not, redirect to index with a message
        if result and result[0] > 0:
            messages.error(request, 'La hora seleccionada ya está ocupada.')
            return redirect('index')

        # check if youre not making appointments for yourself
        if rut_paciente == rut_doctor:
            messages.error(request, 'No puedes pedir una hora a ti mismo.')
            return redirect('form_cita')

        # check if you already have an appointment with the doctor (you cant have more than one appointment with the same doctor)
        with connection.cursor() as cursor:
            cursor.callproc('sp_verificarCitaPendiente', [rut_paciente, rut_doctor])
            cita_pendiente = cursor.fetchone()

        if cita_pendiente and cita_pendiente[0] > 0:
            messages.error(request, 'Ya tienes una cita pendiente con este doctor. Elige a otro.')
            return redirect('form_cita')

        with connection.cursor() as cursor:
            cursor.execute("SELECT nombre FROM usuario WHERE rut = %s", (rut_doctor,))
            doctor = cursor.fetchone()
            print("pedir_hora: nombre del doctor: " + doctor[0])

        # if the appointment is available, store it
        with connection.cursor() as cursor:
            cursor.callproc('sp_insertarCita', [fecha, rut_paciente, rut_doctor, razon, hora])

        # success message and redirect
        messages.success(request, f"Cita registrada con éxito. Le llegará a su correo la información que ingresó. ¡Te esperamos!")

        # send the mail with the details
        sendMailHoraRegistrada(request.session.get('correo'), request.session.get('nombre'), doctor[0], fecha, hora, razon)
        return redirect('index')

    # if youre trying to avoid all the validations without filling the form, you cant.
    messages.error(request, 'No puedes hacer eso.')
    return redirect('index')

# doctor index
def index_medicos(request):
    hoy = timezone.localdate()
    hora = timezone.localtime()
    print("index_medicos: día " + str(hoy))
    print("index_medicos: hora " + str(hora))
    # if the user is not a doctor, or, you dont have an active session, redirect
    if not request.session.get('rut') or request.session.get('medico') != 1:
        messages.error(request, 'Debes iniciar sesión como médico para ver esa página.')
        return redirect('index')

    # if session, get session data
    rut = request.session.get('rut')
    nombre = request.session.get('nombre')
    apellido = request.session.get('apellido')
    print("index_medicos: sesión encontrada: " + rut + " " + nombre + " " + apellido)

    # we search for past appointments
    with connection.cursor() as cursor:
        cursor.callproc('sp_obtenerCitasPasadas', [rut])
        citas_pasadas = cursor.fetchall()
        print("index_medicos: citas pasadas: " + str(citas_pasadas))

    # search for today appointments
    with connection.cursor() as cursor:
        cursor.callproc('sp_obtenerCitasHoy', [rut])
        citas_hoy = cursor.fetchall()
        print("index_medicos: citas hoy: " + str(citas_hoy))

    # search for coming appointments (7 days)
    with connection.cursor() as cursor:
        cursor.callproc('sp_obtenerCitasProxSemana', [rut])
        citas_proximas = cursor.fetchall()
        print("index_medicos: citas próximas: " + str(citas_proximas))

    # future dates (more than 7 days)
    with connection.cursor() as cursor:
        cursor.callproc('sp_obtenerCitasFuturas', [rut])
        citas_futuras = cursor.fetchall()
        print("index_medicos: citas futuras: " + str(citas_futuras))

    # Prepare all the info to send the context
    context = {
        'rut': rut,
        'nombre': nombre,
        'apellido': apellido,
        'citas_pasadas': citas_pasadas,
        'citas_hoy': citas_hoy,
        'citas_proximas': citas_proximas,
        'citas_futuras': citas_futuras
    }

    return render(request, 'cecosf/index_medicos.html', context)

def perfil(request):
    rut = request.session.get('rut')
    if rut:
        with connection.cursor() as cursor:
            cursor.callproc('sp_obtenerDatosUsuario', [rut])
            usuario = cursor.fetchone()
            if usuario:
                usuario_data = {
                    'rut': usuario[0],
                    'nombre': usuario[1],
                    'apellido': usuario[2],
                    'correo': usuario[3],
                    'medico': 'Paciente' if usuario[5] == 0 else 'Médico',
                    'validado': usuario[6],
                    'telefono': usuario[7],
                    'edad': usuario[8],
                    'numhijos': usuario[9],
                    'direccion': usuario[10]
                }
                usuario_data = {k: (v if v is not None else "[No informado]") for k, v in usuario_data.items()}
                context = {'usuario': usuario_data}
                print("perfil: este usuario tenemos: " + str(usuario_data))
            else:
                messages.error(request, 'No se encontró un usuario con ese rut. Inicie sesión nuevamente')
                return redirect('index')

        with connection.cursor() as cursor:
            cursor.callproc('sp_verProximaCitaUsuario', [rut])
            cita = cursor.fetchone()
            if cita:
                cita_data = {
                    'fecha': cita[0],
                    'hora': cita[1],
                    'rut_doctor': cita[2],
                    'razonConsulta': cita[3]
                }
                context['cita'] = cita_data
                print("perfil: próxima cita encontrada: " + str(cita_data))
            else:
                print("perfil: no se encontraron citas para este usuario")

    else:
        messages.error(request, 'Debes iniciar sesión para ver tu perfil.')
        return redirect('index')

    return render(request, 'cecosf/perfil.html', context)

# prepare the info for edit profile page
def editar_perfil(request):
    # check rut of active session
    rut = request.session.get('rut')

    if rut:
        with connection.cursor() as cursor:
            # with that, get all the info
            cursor.callproc('sp_obtenerDatosUsuario', [rut])
            usuario = cursor.fetchone()

            if usuario:
                usuario_data = {
                    'rut': usuario[0],
                    'nombre': usuario[1],
                    'apellido': usuario[2],
                    'correo': usuario[3],
                    'contrasena': usuario[4],
                    'medico': usuario[5],
                    'telefono': usuario[7],
                    'edad': usuario[8],
                    'numhijos': usuario[9],
                    'direccion': usuario[10]
                }
                # replace all the "None" values with ""
                usuario_data = {k: (v if v is not None else "") for k, v in usuario_data.items()}
                context = {'usuario': usuario_data}
            else:
                messages.error(request, 'No se encontró un usuario con ese rut. Inicie sesión nuevamente')
                return redirect('index')
    else:
        messages.error(request, 'Debes iniciar sesión para editar tu perfil.')
        print("editar_perfil: No se encontró un usuario con ese rut")
        return redirect('index')

    return render(request, 'cecosf/editarPerfil.html', context)

# update user
def guardar_datos(request):
    rut = request.session.get('rut')
    print("guardar_datos: se recibió este rut: " + str(rut))

    # if there are not session, redirect
    if not request.session.get('rut'):
        messages.error(request, 'Debes iniciar sesión para hacer eso')
        return redirect('index')

    if request.method == "POST":
        # get all the form data
        nombre = request.POST['nombre']
        apellido = request.POST['apellido']
        telefono = request.POST['telefono']

        # check if rut is not text
        if not telefono.isdigit():
            print("registrar_usuario: RUT no es un número.")
            messages.error(request, "El teléfono ingresado no es válido.")
            return redirect('editar_perfil')

        edad = request.POST['edad']
        correo = request.POST['correo']
        numhijos = request.POST['hijos']
        direccion = request.POST['direccion']

        # convert to none all the empty inputs
        if not edad:
            edad = None
        if not numhijos:
            numhijos = None
        if not direccion:
            direccion = None
        if not telefono:
            telefono = None

        with connection.cursor() as cursor:
            try:
                # update data
                cursor.callproc('sp_actualizarUsuario', [rut, nombre, apellido, correo])
                cursor.callproc('sp_actualizarUsuarioDetalles', [rut, telefono, edad, numhijos, direccion])

                # verify if the mail is different
                correo_actual = request.session.get('correo')
                if correo != correo_actual:
                    print("guardar_datos: el correo cambió, enviando correo de validación y desactivando funciones")
                    # set validate to 0
                    cursor.execute("UPDATE usuario SET validado = 0 WHERE rut = %s", (rut,))

                    # delete old token
                    cursor.execute("DELETE FROM validacion_token WHERE rut_usuario = %s", (rut,))

                    # generate new token
                    nuevo_token = generar_token()

                    # insert new token into the database
                    cursor.execute("INSERT INTO validacion_token (rut_usuario, token, fecha_creacion) VALUES (%s, %s, %s)", (rut, nuevo_token, timezone.now()))

                    # send the token to new mail
                    url_validar = f'{sitio}/validar_token?token={nuevo_token}'
                    sendMailValidar(correo, nombre, url_validar)

                    # update mail
                    request.session['correo'] = correo
                    request.session['validado'] = 0

                    # tell the user that new validate is needed
                    messages.info(request, 'Tu correo ha sido actualizado. Por favor, valida tu nuevo correo electrónico para seguir pidiendo horas.')
                else:
                    print("guardar_datos: el correo no cambió, no hacemos nada.")

                # replace the user cache for new possible names or other info
                request.session['nombre'] = nombre
                request.session['apellido'] = apellido

                print("guardar_datos: Datos actualizados correctamente")
                messages.success(request, 'Datos actualizados correctamente.')
                return redirect('index')

            except IntegrityError as e:
                print("Error al actualizar los datos del usuario: " + str(e))
                messages.error(request, 'Hubo un error al actualizar tus datos.')
                return redirect('index')
    else:
        print("guardar_datos: Parece que no puedes hacer eso.")
        messages.error(request, 'No puedes actualizar tus datos sin usar el formulario adecuado. ¿Qué vas a actualizar?')
        return redirect('index')

# view for new announcements
def nuevo_anuncio(request):
    # check session because medical session is needed
    if not request.session.get('rut') or request.session.get('medico') != 1:
        messages.error(request, 'Debes iniciar sesión como médico para ver esa página.')
        return redirect('index')

    fecha = datetime.now()
    if not request.session.get('rut') or request.session.get('medico') != 1:
        messages.error(request, 'Debes iniciar sesión como médico para ver esa página.')
        return redirect('index')

    # if doctor session, load the page
    return render(request, 'cecosf/nuevo_anuncio.html', {'fecha': fecha})

def guardar_anuncio(request):
    # again, check session requirements
    if not request.session.get('rut') or request.session.get('medico') != 1:
        messages.error(request, 'Debes iniciar sesión como médico para ver esa página.')
        return redirect('index')

    if request.method == "POST":
        titulo = request.POST['titulo']
        contenido = request.POST['contenido']
        fecha = datetime.now()

        # save the announcement
        with connection.cursor() as cursor:
            cursor.callproc('sp_insertarAnuncio', [titulo, contenido, fecha])
            print("guardar_anuncio: Anuncio guardado correctamente")

            messages.success(request, 'Anuncio publicado correctamente.')
            return redirect('index_medicos')
    else:
        print("guardar_anuncio: Parece que no puedes hacer eso.")
        return redirect('index')

def administrar_datos(request):
    print("eliminar_datos: cargando los datos")

    # session requirements
    if not request.session.get('rut') or request.session.get('medico') != 1:
        messages.error(request, 'Debes iniciar sesión como médico para ver esa página.')
        return redirect('index')

    rut = request.session.get('rut')
    nombre = request.session.get('nombre')

    usuario_data = {}

    # check all registered users
    with connection.cursor() as cursor:
        # 'usuarios_registrados' is a view
        cursor.execute("SELECT * FROM usuarios_registrados")
        usuarios = cursor.fetchall()
        usuario_data = [
            {
                'rut': usuario[0],
                'nombre': usuario[1],
                'apellido': usuario[2],
                'correo': usuario[3],
                'contrasena': usuario[4],
                'medico': 'Sí' if usuario[5] == 1 else 'No',
                'validado': 'Sí' if usuario[6] == 1 else 'No',
                'telefono': usuario[7] if usuario[7] is not None else '[No informado]',
                'edad': usuario[8] if usuario[8] is not None else '[No informado]',
                'numhijos': usuario[9] if usuario[9] is not None else '[No informado]',
                'direccion': usuario[10] if usuario[10] is not None else '[No informado]',
            }
            for usuario in usuarios
        ]

    # announcements
    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM anuncios_desc")
        anuncios = cursor.fetchall()
        # prepare the data
        anuncios_list = [
            {
                "id": anuncio[0],
                "titulo": anuncio[1],
                "contenido": anuncio[2],
                "fecha": anuncio[3]
            }
            for anuncio in anuncios
        ]

    with connection.cursor() as cursor:
        cursor.execute("SELECT * FROM citas_detalle")
        citas = cursor.fetchall()

        citas_list = [
            {
                "id": cita[0],
                "fecha": cita[1],
                "hora": cita[2],
                "paciente": cita[3],
                "doctor": cita[4],
                "razon_consulta": cita[5]
            }
            for cita in citas
        ]

    return render(request, 'cecosf/administrar_datos.html', {"usuarios": usuario_data, "anuncios": anuncios_list, "citas": citas_list, "rut": rut, "nombre": nombre})

def eliminar_anuncio(request, id):
    # session requirements
    if not request.session.get('rut') or request.session.get('medico') != 1:
        messages.error(request, 'Debes iniciar sesión como médico para hacer eso.')
        return redirect('index')

    print("eliminar_anuncio: se recibió el anuncio con el id " + id)

    with connection.cursor() as cursor:
        cursor.callproc('sp_borrarAnuncio', [id])
        print("Eliminado")

    messages.success(request, 'Anuncio eliminado correctamente.')
    return redirect('administrar_datos')

def eliminar_hora(request, id):
    # ssession requirements
    if not request.session.get('rut'):
        messages.error(request, 'No puedes hacer eso')
        return redirect('index')

    print("eliminar_hora: se recibió la hora con el id " + id)

    with connection.cursor() as cursor:
        cursor.callproc('sp_borrarCita', [id])
        print("Eliminado")

    if request.session.get('medico') == 1:
        messages.success(request, 'Hora eliminada correctamente.')
        return redirect('administrar_datos')
    messages.success(request, 'Hora eliminada correctamente.')
    return redirect('index')

def eliminar_usuario(request, rut):
    #session requirements
    if not request.session.get('rut') or request.session.get('medico') != 1:
        messages.error(request, 'Debes iniciar sesión como médico para hacer eso.')
        return redirect('index')

    print("eliminar_usuario: se recibió el usuario con el rut " + rut)

    # check if the user are not deleting himself
    if rut == request.session.get('rut'):
        print("eliminar_usuario: intento de eliminarse a si mismo.")
        messages.error(request, 'Usuario no eliminado: Ups. ¿Te quieres eliminar a ti mismo?')
        return redirect('administrar_datos')

    print("eliminar_usuario: eliminando las citas del usuario si es paciente o doctor")
    with connection.cursor() as cursor:
        cursor.callproc("sp_borrarCitaUsuario", [rut])
        print("Eliminado")

    print("eliminar_usuario: eliminando los detalles del usuario.")
    with connection.cursor() as cursor:
        cursor.callproc('sp_borrarDetallesUsuario', [rut])
        print("Eliminado")

    print("eliminar_usuario: eliminando al usuario.")
    with connection.cursor() as cursor:
        cursor.callproc('sp_borrarUsuario', [rut])
        print("Eliminado")

    messages.success(request, 'Usuario eliminado correctamente.')
    return redirect('administrar_datos')

def cancelar_hora(request):
    print("cancelar_hora: cargando información")

    rut = request.session.get('rut')
    validado = request.session.get('validado')

    if rut:
        if validado == 0:
            messages.error(request, 'Debes validar tu cuenta antes de cancelar una hora.')
            return redirect('index')

        nombre = request.session.get('nombre')

        print("cancelar_hora: nombre: " + nombre)

        with connection.cursor() as cursor:
            cursor.callproc('sp_obtenerCitasPaciente', [rut])
            citas = cursor.fetchall()

            # prepare the data
            citas_list = [
                {
                    "id": cita[0],
                    "fecha": cita[1],
                    "hora": cita[2],
                    "paciente": rut,
                    "doctor": cita[4],
                    "razon": cita[5],
                }
                for cita in citas
            ]

            print("Citas encontradas")
            print(citas_list)

            context = {
                "nombre": nombre,
                "rut": rut,
                "citas": citas_list
            }
    else:
        print("cancelar_hora: no hay sesión")
        messages.error(request, "Debes iniciar sesión para hacer eso")
        return redirect('index')

    return render(request, 'cecosf/cancelar_hora.html', context)
