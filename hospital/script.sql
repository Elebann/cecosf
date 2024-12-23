CREATE DATABASE cecosf; -- solo para trabajar db local
USE cecosf; -- solo para db local

CREATE TABLE usuario (
  rut INT PRIMARY KEY,
  nombre VARCHAR(36) NOT NULL,
  apellido VARCHAR(36) NOT NULL,
  correo VARCHAR(50) NOT NULL,
  contrasena VARCHAR(256) NOT NULL,
  medico BOOLEAN NOT NULL,
  validado BOOLEAN DEFAULT 0
);

CREATE TABLE validacion_token(
    id INT PRIMARY KEY AUTO_INCREMENT,
    rut_usuario INT NOT NULL,
    token VARCHAR(256) NOT NULL,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usado BOOLEAN DEFAULT 0,
    FOREIGN KEY (rut_usuario) REFERENCES usuario(rut)
);

CREATE TABLE usuario_detalles (
  id INT PRIMARY KEY AUTO_INCREMENT,
  rut_usuario INT,
  telefono INT,
  edad INT,
  numhijos INT,
  direccion VARCHAR(120),
  FOREIGN KEY (rut_usuario) REFERENCES usuario(rut)
);

CREATE TABLE cita (
  id INT PRIMARY KEY AUTO_INCREMENT,
  fecha DATE,
  rut_paciente INT,
  rut_doctor INT,
  razonConsulta VARCHAR(512),
  hora TIME,
  FOREIGN KEY (rut_paciente) REFERENCES usuario(rut),
  FOREIGN KEY (rut_doctor) REFERENCES usuario(rut)
);

CREATE TABLE anuncios (
  id INT PRIMARY KEY AUTO_INCREMENT,
  titulo VARCHAR(50),
  contenido VARCHAR(128),
  fecha DATE DEFAULT CURRENT_TIMESTAMP
);

-- PROCEDIMIENTOS ALMACENADOS y VISTAS

-- para validar usuarios (rut y contraseña)
DELIMITER //
CREATE PROCEDURE sp_validarUsuario(IN rut_param INT, IN contrasena_param VARCHAR(50))
BEGIN
    SELECT * FROM usuario WHERE rut = rut_param AND contrasena = contrasena_param;
END //
DELIMITER ;

-- para agregar a un nuevo usuario
DELIMITER //
CREATE PROCEDURE sp_insertarUsuario(IN rut_param INT, IN nombre_param VARCHAR(36), IN apellido_param VARCHAR(36), IN correo_param VARCHAR(50), IN contrasena_param VARCHAR(256), IN medico_param BOOLEAN)
BEGIN
    INSERT INTO usuario (rut, nombre, apellido, correo, contrasena, medico)
    VALUES (rut_param, nombre_param, apellido_param, correo_param, contrasena_param, medico_param);
END //
DELIMITER ;

-- sp para ingresar los token de validación de los usuarios
DELIMITER //
CREATE PROCEDURE sp_insertarToken(IN rut_param INT, IN token_param VARCHAR(256))
BEGIN
    INSERT INTO validacion_token (rut_usuario, token)
    VALUES (rut_param, token_param);
END //
DELIMITER ;

-- para agregar los detalles del usuario
DELIMITER //
CREATE PROCEDURE sp_insertarUsuarioDetalles(IN rut_usuario_param INT, IN telefono_param INT, IN edad_param INT, IN numhijos_param INT, IN direccion_param VARCHAR(120))
BEGIN
    INSERT INTO usuario_detalles (rut_usuario, telefono, edad, numhijos, direccion)
    VALUES (rut_usuario_param, telefono_param, edad_param, numhijos_param, direccion_param);
END //
DELIMITER ;

-- vista para consultar a todos los médicos. (Para cuando estamos pidiendo una hora y necesitamos seleccionar al médico)
CREATE VIEW medicos AS
SELECT * FROM usuario WHERE medico = 1;

CREATE VIEW anuncios_recientes AS
    SELECT * FROM anuncios ORDER BY id DESC LIMIT 6;

-- sp para consultar las horas disponibles de un doctor
DELIMITER //
CREATE PROCEDURE sp_horasDisponibles(IN doctor_rut_param INT, IN fecha_param DATE)
BEGIN
    SELECT TIME_FORMAT(hora, '%H:%i') AS hora
    FROM cita
    WHERE rut_doctor = doctor_rut_param AND fecha = fecha_param;
END //
DELIMITER ;

-- sp para ver si la hora ya se seleccionó
DELIMITER //
CREATE PROCEDURE sp_verificarDisponibilidad(IN doctor_rut_param INT, IN fecha_param DATE, IN hora_param TIME)
BEGIN
    SELECT COUNT(*)
    FROM cita
    WHERE rut_doctor = doctor_rut_param AND fecha = fecha_param AND TIME_FORMAT(hora, '%H:%i') = TIME_FORMAT(hora_param, '%H:%i');
END //
DELIMITER ;

-- sp para insertar las citas
DELIMITER //
CREATE PROCEDURE sp_insertarCita(IN fecha_param DATE, IN rut_paciente_param INT, IN rut_doctor_param INT, IN razonConsulta_param VARCHAR(512), IN hora_param TIME)
BEGIN
    INSERT INTO cita (fecha, rut_paciente, rut_doctor, razonConsulta, hora)
    VALUES (fecha_param, rut_paciente_param, rut_doctor_param, razonConsulta_param, hora_param);
END //
DELIMITER ;

-- en el index del medico rescatamos todas las citas agendadas a su rut. aqui esta su sp
DELIMITER //
CREATE PROCEDURE sp_obtenerCitasMedico(IN rut_doctor_param INT)
BEGIN
    SELECT cita.fecha, cita.hora, p.nombre, cita.razonConsulta
    FROM cita
    JOIN usuario p on p.rut = cita.rut_paciente
    WHERE cita.rut_doctor = rut_doctor_param
    ORDER BY fecha ASC;
END //
DELIMITER ;

-- sp para ver las citas pasadas de un médico
DELIMITER //
CREATE PROCEDURE sp_obtenerCitasPasadas(IN rut_doctor_param INT)
BEGIN
    SELECT cita.fecha, cita.hora, p.nombre, cita.razonConsulta
    FROM cita
    JOIN usuario p ON p.rut = cita.rut_paciente
    WHERE cita.rut_doctor = rut_doctor_param AND (cita.fecha < CURDATE() OR (cita.fecha = CURDATE() AND cita.hora < CURTIME()))
    ORDER BY cita.fecha ASC, cita.hora ASC;
END //
DELIMITER ;

-- sp para ver las citas de hoy de un médico (las que ya pasaron de la hora de hoy no se muestran)
DELIMITER //
CREATE PROCEDURE sp_obtenerCitasHoy(IN rut_doctor_param INT)
BEGIN
    SELECT cita.fecha, cita.hora, p.nombre, cita.razonConsulta
    FROM cita
    JOIN usuario p ON p.rut = cita.rut_paciente
    WHERE cita.rut_doctor = rut_doctor_param AND cita.fecha = CURDATE() AND cita.hora >= CURTIME()
    ORDER BY cita.fecha ASC, cita.hora ASC;
END //
DELIMITER ;

-- sp para ver las citas de los próximos 7 días de un médico (excluyendo hoy)
DELIMITER //
CREATE PROCEDURE sp_obtenerCitasProxSemana(IN rut_doctor_param INT)
BEGIN
    SELECT cita.fecha, cita.hora, p.nombre, cita.razonConsulta
    FROM cita
    JOIN usuario p ON p.rut = cita.rut_paciente
    WHERE cita.rut_doctor = rut_doctor_param AND cita.fecha > CURDATE() AND cita.fecha <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
    ORDER BY cita.fecha ASC, cita.hora ASC;
END //
DELIMITER ;

DELIMITER //
CREATE PROCEDURE sp_obtenerCitasFuturas(IN rut_doctor_param INT)
BEGIN
    SELECT cita.fecha, cita.hora, p.nombre, cita.razonConsulta
    FROM cita
    JOIN usuario p ON p.rut = cita.rut_paciente
    WHERE cita.rut_doctor = rut_doctor_param AND cita.fecha > DATE_ADD(CURDATE(), INTERVAL 7 DAY)
    ORDER BY cita.fecha ASC, cita.hora ASC;
END //
DELIMITER ;

-- (desfase -4h de railway) (estas se están usando)
DELIMITER //
CREATE PROCEDURE sp_obtenerCitasPasadas(IN rut_doctor_param INT)
BEGIN
    SELECT cita.fecha, cita.hora, p.nombre, cita.razonConsulta
    FROM cita
    JOIN usuario p ON p.rut = cita.rut_paciente
    WHERE cita.rut_doctor = rut_doctor_param
    AND (cita.fecha < CURDATE() OR (cita.fecha = CURDATE() AND cita.hora < DATE_SUB(CURTIME(), INTERVAL 4 HOUR)))
    ORDER BY cita.fecha ASC, cita.hora ASC;
END //
DELIMITER ;

DELIMITER //
CREATE PROCEDURE sp_obtenerCitasHoy(IN rut_doctor_param INT)
BEGIN
    SELECT cita.fecha, cita.hora, p.nombre, cita.razonConsulta
    FROM cita
    JOIN usuario p ON p.rut = cita.rut_paciente
    WHERE cita.rut_doctor = rut_doctor_param
    AND cita.fecha = CURDATE()
    AND cita.hora >= DATE_SUB(CURTIME(), INTERVAL 4 HOUR)
    ORDER BY cita.fecha ASC, cita.hora ASC;
END //
DELIMITER ;


DELIMITER //
CREATE PROCEDURE sp_verUsuario(IN rut_param INT)
BEGIN
    SELECT * FROM usuario WHERE rut = rut_param;
END //
DELIMITER ;

-- sp para obtener todos los datos de un paciente ya sea tabla usuario y usuario_detalles
DELIMITER //
CREATE PROCEDURE sp_obtenerDatosUsuario(IN rut_param INT)
BEGIN
    SELECT
        usuario.rut,
        usuario.nombre,
        usuario.apellido,
        usuario.correo,
        usuario.contrasena,
        usuario.medico,
        usuario.validado,
        usuario_detalles.telefono,
        usuario_detalles.edad,
        usuario_detalles.numhijos,
        usuario_detalles.direccion
    FROM
        usuario
    LEFT JOIN
        usuario_detalles ON usuario.rut = usuario_detalles.rut_usuario
    WHERE
        usuario.rut = rut_param;
END //
DELIMITER ;

-- sp para actualizar los datos de un usuario
DELIMITER //
CREATE PROCEDURE sp_actualizarUsuario(IN rut_param INT, IN nombre_param VARCHAR(36), IN apellido_param VARCHAR(36), IN correo_param VARCHAR(50), IN contrasena_param VARCHAR(256))
BEGIN
    UPDATE usuario
    SET nombre = nombre_param, apellido = apellido_param, correo = correo_param, contrasena = contrasena_param
    WHERE rut = rut_param;
END //
DELIMITER ;

-- sp para actualizar los detalles de un usuario
DELIMITER //
CREATE PROCEDURE sp_actualizarUsuarioDetalles(IN rut_param INT, IN telefono_param INT, IN edad_param INT, IN numhijos_param INT, IN direccion_param VARCHAR(120))
BEGIN
    UPDATE usuario_detalles
    SET telefono = telefono_param, edad = edad_param, numhijos = numhijos_param, direccion = direccion_param
    WHERE rut_usuario = rut_param;
END //
DELIMITER ;

-- sp para insertar los anuncios
DELIMITER //
CREATE PROCEDURE sp_insertarAnuncio(IN titulo_param VARCHAR(50), IN contenido_param VARCHAR(128), IN fecha_param DATE)
BEGIN
    INSERT INTO anuncios (titulo, contenido, fecha) VALUES (titulo_param, contenido_param, fecha_param);
END //
DELIMITER ;

-- vista para obtener los anuncios ordenados por id descendente
CREATE VIEW anuncios_desc AS
    SELECT * FROM anuncios ORDER BY id DESC;

-- vista para obtener todas las citas con los respectivos joins para camuflar la relacion entre tablas
CREATE VIEW citas_detalle AS
    SELECT cita.id, cita.fecha, cita.hora, p.nombre as paciente, d.nombre as doctor, cita.razonConsulta
    FROM cita
    JOIN usuario p on p.rut = cita.rut_paciente
    JOIN usuario d on d.rut = cita.rut_doctor
    ORDER BY id ASC;

-- sp para borrar los anuncios
DELIMITER //
CREATE PROCEDURE sp_borrarAnuncio(IN id_param INT)
BEGIN
    DELETE FROM anuncios WHERE id = id_param;
END //
DELIMITER ;

-- sp para borrar las citas
DELIMITER //
CREATE PROCEDURE sp_borrarCita(IN id_param INT)
BEGIN
    DELETE FROM cita WHERE id = id_param;
END //
DELIMITER ;

-- sp para borrar los detalles de un usuario
DELIMITER //
CREATE PROCEDURE sp_borrarDetallesUsuario(IN rut_param INT)
BEGIN
    DELETE FROM usuario_detalles WHERE rut_usuario = rut_param;
END //
DELIMITER ;

-- sp para borrar un usuario
DELIMITER //
CREATE PROCEDURE sp_borrarUsuario(IN rut_param INT)
BEGIN
    DELETE from validacion_token WHERE rut_usuario = rut_param;
    DELETE FROM usuario WHERE rut = rut_param;
END //
DELIMITER ;

-- sp para borrar todas las citas de un usuario ya sea paciente o doctor
DELIMITER //
CREATE PROCEDURE sp_borrarCitaUsuario(IN rut_param INT)
BEGIN
    DELETE FROM cita WHERE rut_doctor = rut_param OR rut_paciente = rut_param;
END //
DELIMITER ;

-- sp para obtener la contraseña de un usuario (para obtener el hash)
DELIMITER //
CREATE PROCEDURE sp_obtenerContrasena(IN rut_param INT)
BEGIN
    SELECT contrasena
    FROM usuario
    WHERE rut = rut_param;
END //
DELIMITER ;

-- sp para obtener las citas de un usuario
DELIMITER //
CREATE PROCEDURE sp_obtenerCitasPaciente(IN rut_paciente_param INT)
BEGIN
    SELECT cita.id, cita.fecha, cita.hora, cita.rut_paciente, usuario.nombre AS doctor, cita.razonConsulta
    FROM cita
    JOIN usuario ON cita.rut_doctor = usuario.rut
    WHERE cita.rut_paciente = rut_paciente_param;
END //
DELIMITER ;

DELIMITER //
CREATE PROCEDURE sp_buscarToken(IN token_param VARCHAR(255))
BEGIN
    SELECT rut_usuario, usado, fecha_creacion FROM validacion_token WHERE token = token_param;
END //
DELIMITER ;

DELIMITER //
CREATE PROCEDURE sp_validarUsuarioYToken(IN rut_param INT, IN token_param VARCHAR(255))
BEGIN
    UPDATE usuario SET validado = 1 WHERE rut = rut_param;
    UPDATE validacion_token SET usado = 1 WHERE token = token_param;
END //
DELIMITER ;

DELIMITER //
CREATE PROCEDURE sp_verProximaCitaUsuario(IN rut_paciente_param INT)
BEGIN
    SELECT cita.fecha, cita.hora, doctor.nombre AS doctor, cita.razonConsulta
    FROM cita
    JOIN usuario AS doctor ON cita.rut_doctor = doctor.rut
    WHERE cita.rut_paciente = rut_paciente_param AND (cita.fecha > CURDATE() OR (cita.fecha = CURDATE() AND cita.hora > CURTIME()))
    ORDER BY fecha
    LIMIT 1;
END //
DELIMITER ;

DELIMITER //
CREATE PROCEDURE sp_verificarCitaPendiente(IN rut_paciente_param INT, IN rut_doctor_param INT)
BEGIN
    SELECT COUNT(*) FROM cita WHERE rut_paciente = rut_paciente_param AND rut_doctor = rut_doctor_param AND fecha >= CURDATE();
END //
DELIMITER ;