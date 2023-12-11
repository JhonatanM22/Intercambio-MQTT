import paho.mqtt.client as mqtt
import psutil
import platform
import datetime
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import mysql.connector

# Configuración del broker MQTT
broker_address = "broker.hivemq.com"
port = 1883
topic = "mateo"
#Topico al que se enviará la información
topic_diferencia_metadatos = "metadatos"

# Configuración de la base de datos MySQL
db_host = "tu_host"
db_user = "tu_usuario"
db_password = "tu_contraseña"
db_name = "nombre_de_tu_base_de_datos"

# Configuración del servidor SMTP para enviar correos
smtp_server = "smtp.gmail.com"
smtp_port = 587
smtp_username = "mmales385@gmail.com"
smtp_password = "acir fpif edes uzsq"
recipient_email = "mateomales2003@gmail.com"

# Función para conectar a la base de datos
def conectar_base_de_datos():
    try:
        connection = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name
        )
        return connection
    except mysql.connector.Error as err:
        print(f"Error al conectar a la base de datos: {err}")
        return None

# Función para obtener la fecha actual
def obtener_fecha_actual():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Función que se ejecuta cuando se conecta al broker
def on_connect(client, userdata, flags, rc):
    print(f"Conectado con código de resultado {rc}")
    client.subscribe(topic)

# Función que se ejecuta cuando se recibe un mensaje
def on_message(client, userdata, msg):
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    mensaje_completo = f"\nMensaje recibido el {fecha_actual}:\n {msg.payload.decode()}"
    print(mensaje_completo)


# Función para obtener el rendimiento del CPU
def obtener_rendimiento_cpu():
    return psutil.cpu_percent(interval=1)

# Función para obtener el rendimiento de la memoria
def obtener_rendimiento_memoria():
    return psutil.virtual_memory().percent

# Función para obtener el rendimiento de la red
def obtener_rendimiento_red():
    return psutil.net_io_counters().bytes_recv / 1024**3

# Función para obtener el sistema operativo
def obtener_sistema_operativo():
    return platform.system()

# Función para enviar un correo de alerta
def enviar_alerta():
    subject = "Alerta: Rendimiento del CPU superior al 40%"
    body = "El rendimiento del CPU ha superado el 40%. Verifica el estado de la computadora."

    # Configuración del mensaje
    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    # Conexión al servidor SMTP y envío del correo
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, recipient_email, msg.as_string())

    print("Correo de alerta enviado.")

# Función para verificar y enviar alerta si el rendimiento del CPU es mayor al 40%
def verificar_y_enviar_alerta(mensaje):
    # Busca la línea que contiene el rendimiento del CPU en el mensaje
    linea_cpu = next((linea for linea in mensaje.split('\n') if 'Rendimiento del CPU' in linea), None)

    if linea_cpu:
        try:
            # Extrae el valor del rendimiento del CPU y lo convierte a float
            rendimiento_cpu = float(linea_cpu.split(":")[1].strip().replace("%", ""))
            if rendimiento_cpu > 40:
                enviar_alerta()
        except ValueError:
            print("Error al convertir el rendimiento del CPU a un número.")

# Función para calcular la diferencia entre dos conjuntos de metadatos y enviarla
def calcular_diferencia_y_enviar(mensaje):
    # Recolecta datos de rendimiento del segundo equipo
    rendimiento_cpu_segundo_equipo = obtener_rendimiento_cpu()
    rendimiento_memoria_segundo_equipo = obtener_rendimiento_memoria()
    rendimiento_red_segundo_equipo = obtener_rendimiento_red()
    sistema_operativo_segundo_equipo = obtener_sistema_operativo()

    # Formatea los datos como un mensaje del segundo equipo
    mensaje_segundo_equipo = (
        f"Rendimiento del CPU (%): {rendimiento_cpu_segundo_equipo}\n"
        f"Rendimiento de la Memoria (%): {rendimiento_memoria_segundo_equipo}\n"
        f"Rendimiento de la Red (GB): {rendimiento_red_segundo_equipo}\n"
        f"Sistema Operativo: {sistema_operativo_segundo_equipo}"
    )

    # Calcula la diferencia entre los dos conjuntos de metadatos
    diferencia_metadatos = "Diferencia en metadatos:\n"
    for linea_equipo1, linea_equipo2 in zip(mensaje.split('\n'), mensaje_segundo_equipo.split('\n')):
        if ':' in linea_equipo1 and ':' in linea_equipo2:
            clave1, valor1 = [parte.strip() for parte in linea_equipo1.split(':')]
            clave2, valor2 = [parte.strip() for parte in linea_equipo2.split(':')]
            if clave1 == clave2:
                try:
                    diferencia = float(valor1.replace('%', '')) - float(valor2.replace('%', ''))
                    diferencia_metadatos += f"{clave1}: {diferencia}\n"
                except ValueError:
                    print(f"Error al calcular la diferencia para {clave1}.")

    # Enviar la diferencia al tópico correspondiente
    client.publish(topic_diferencia_metadatos, diferencia_metadatos)
    print("Diferencia de metadatos enviada:\n", diferencia_metadatos)


# Configuración del cliente MQTT
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Conexión al broker
client.connect(broker_address, port, 60)
client.loop_start()

try:
    while True:
        # Recolecta datos de rendimiento
        rendimiento_cpu = obtener_rendimiento_cpu()
        rendimiento_memoria = obtener_rendimiento_memoria()
        rendimiento_red = obtener_rendimiento_red()
        sistema_operativo = obtener_sistema_operativo()
        fecha_actual = obtener_fecha_actual()  # Agrega la fecha actual

        # Formatea los datos como un mensaje
        mensaje = (
            f"Fecha y Hora del mensaje: {fecha_actual}\n"
            f"Rendimiento del CPU (%): {rendimiento_cpu}\n"
            f"Rendimiento de la Memoria (%): {rendimiento_memoria}\n"
            f"Rendimiento de la Red (GB): {rendimiento_red}\n"
            f"Sistema Operativo: {sistema_operativo}"
        )

        # Envia el mensaje al broker MQTT
        client.publish(topic, mensaje)

        # Limpia el búfer de la consola
        os.system('cls' if os.name == 'nt' else 'clear')

        # Imprime el mensaje para el usuario
        print("Mensaje enviado:\n", mensaje)

        # Verifica y envía una alerta si es necesario
        verificar_y_enviar_alerta(mensaje)

        # Espera a que el usuario presione ENTER para enviar el siguiente mensaje
        input("\nPresiona ENTER para enviar el siguiente mensaje...\n")


except KeyboardInterrupt:
    # Desconectar al recibir una interrupción del teclado (Ctrl+C)
    client.disconnect()
    client.loop_stop()
