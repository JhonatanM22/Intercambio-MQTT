import paho.mqtt.client as mqtt
import psutil
import platform
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# Configuración de la base de datos MySQL
db_host = "localhost"
db_user = "root"
db_password = "K4m1s4T0.Ayak4"
db_name = "Arquitectura"

# Configuración del broker MQTT
broker_address = "broker.hivemq.com"
port = 1883
topic = "metadatos"
#Topico al que se enviará la información
topic_diferencia_metadatos = "topico2"

# Configuración del servidor SMTP para enviar correos
smtp_server = "smtp.gmail.com"
smtp_port = 587
smtp_username = "mmales385@gmail.com"
smtp_password = "acir fpif edes uzsq"
recipient_email = "mateomales2003@gmail.com"

# Identificador del equipo (remitente)
remitente = "Mateo"

# Función para conectar a la base de datos MySQL
def conectar_mysql():
    try:
        connection = mysql.connector.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name
        )
        if connection.is_connected():
            print(f"Conectado a la base de datos: {db_name}")
            return connection
    except Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

# Función para insertar datos en la tabla 'data'
def insertar_en_tabla_data(connection, info, percent):
    try:
        cursor = connection.cursor()
        sql_query = "INSERT INTO data (info, percent) VALUES (%s, %s)"
        cursor.execute(sql_query, (info, percent))
        connection.commit()
        print("Datos insertados en la tabla 'data'.")
    except Error as e:
        print(f"Error al insertar datos en la tabla 'data': {e}")

# Función que se ejecuta cuando se conecta al broker
def on_connect(client, userdata, flags, rc):
    print(f"Conectado con código de resultado {rc}")
    client.subscribe(topic)

# Función que se ejecuta cuando se recibe un mensaje
def on_message(client, userdata, msg):
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    remitente_mensaje = msg.topic.split("/")[-1]  # Extrae el remitente del tópico
    print("\nMensaje recibido en {} de {}:\n {}".format(fecha_actual, remitente_mensaje, msg.payload.decode()))

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

        # Formatea los datos como un mensaje
        mensaje = (
            f"PC de: {remitente}\n"
            f"Rendimiento del CPU (%): {rendimiento_cpu}\n"
            f"Rendimiento de la Memoria (%): {rendimiento_memoria}\n"
            f"Rendimiento de la Red (GB): {rendimiento_red}\n"
            f"Sistema Operativo: {sistema_operativo}"
        )

        # Envia el mensaje al broker MQTT
        client.publish(topic, mensaje)

         # Inserta los datos en la tabla 'data' de la base de datos MySQL
        connection = conectar_mysql()
        if connection:
            insertar_en_tabla_data(connection, "PC de", remitente)
            insertar_en_tabla_data(connection, "Rendimiento del CPU", rendimiento_cpu)
            insertar_en_tabla_data(connection, "Rendimiento de la Memoria", rendimiento_memoria)
            insertar_en_tabla_data(connection, "Rendimiento de la Red", rendimiento_red)
            insertar_en_tabla_data(connection, "Sistema Operativo", sistema_operativo)
            connection.close()

         # Obtiene la fecha y hora actual
        fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Limpia el búfer de la consola
        os.system("cls" if os.name == "nt" else "clear")

        # Imprime la fecha y el mensaje para el usuario
        print("Mensaje enviado en {}:\n {}".format(fecha_actual, mensaje))

        # Verifica y envía una alerta si es necesario
        verificar_y_enviar_alerta(mensaje)

        # Espera a que el usuario presione ENTER para enviar el siguiente mensaje
        input("\nPresiona ENTER para enviar el siguiente mensaje...\n")

except KeyboardInterrupt:
    # Desconectar al recibir una interrupción del teclado (Ctrl+C)
    client.disconnect()
    client.loop_stop()
