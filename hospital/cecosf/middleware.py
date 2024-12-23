from django.utils.deprecation import MiddlewareMixin
from django.db import connection

# This file will execute on every refresh or new page
class UpdateUserSessionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.session.get('rut'):
            rut = request.session['rut']

            print("Middleware: Rut en sesión ", rut)

            with connection.cursor() as cursor:
                cursor.execute("SELECT nombre, apellido, correo, validado FROM usuario WHERE rut = %s", [rut])
                user = cursor.fetchone()

                print("Middleware: usuario encontrado ", user)
                if user:
                    request.session['nombre'] = user[0]
                    request.session['apellido'] = user[1]
                    request.session['correo'] = user[2]
                    request.session['validado'] = user[3]