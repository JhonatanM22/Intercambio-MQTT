import paho.mqtt.client as mqtt
import threading
import time
import psutil
import platform
import smtplib
from email.mime.text import MIMEText

# Crear un bloqueo para la sincronización de la salida
print_lock = threading.Lock()

# Configuración para enviar el correo
# Configuración para enviar el correo
correo_emisor = 'mmales385@gmail.com'
contrasena_emisor = 'acir fpif edes uzsq'
correo_destino = 'mateomales2003@gmail.com'

def enviar_correo(asunto, mensaje):
    mensaje_correo = MIMEText(mensaje)
    mensaje_correo['Subject'] = asunto
    mensaje_correo['From'] = correo_emisor
    mensaje_correo['To'] = correo_destino

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as servidor_smtp:
            servidor_smtp.login(correo_emisor, contrasena_emisor)
            servidor_smtp.sendmail(correo_emisor, correo_destino, mensaje_correo.as_string())

        print("Correo enviado exitosamente.")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")


def on_connect(client, userdata, flags, rc):
    with print_lock:
        print(f"Conectado con código de resultado {rc}")
    client.subscribe("metadatos")
    client.subscribe("diferencia_metadatos")

def on_message(client, userdata, msg):
    with print_lock:
        print(f"Mensaje recibido: {msg.payload.decode()}")

def recibir_mensajes(client):
    while True:
        time.sleep(1)  # Añade un pequeño retardo para evitar que bloquee completamente el programa
        client.loop()

def obtener_rendimiento_cpu():
    return psutil.cpu_percent(interval=1)

def obtener_rendimiento_memoria():
    return psutil.virtual_memory().percent

def obtener_rendimiento_red():
    sent_before, recv_before = psutil.net_io_counters().bytes_sent, psutil.net_io_counters().bytes_recv
    psutil.cpu_percent(interval=1)  # Actualiza las métricas mientras esperamos
    sent_after, recv_after = psutil.net_io_counters().bytes_sent, psutil.net_io_counters().bytes_recv

    # Calcular la tasa de transferencia en bytes por segundo
    tasa_envio = sent_after - sent_before
    tasa_recibo = recv_after - recv_before

    return tasa_envio, tasa_recibo

def obtener_sistema_operativo():
    return platform.system()

def obtener_metadatos():
    porcentaje_cpu = obtener_rendimiento_cpu()
    rendimiento_memoria = obtener_rendimiento_memoria()
    tasa_envio_local, tasa_recibo_local = obtener_rendimiento_red()
    sistema_operativo = obtener_sistema_operativo()

    mensaje = f"Rendimiento CPU (%): {porcentaje_cpu}%\n" \
              f"Rendimiento de memoria: {rendimiento_memoria}%\n" \
              f"Tasa de Transferencia - Enviados (bytes/segundo): {tasa_envio_local}\n" \
              f"Tasa de Transferencia - Recibidos (bytes/segundo): {tasa_recibo_local}\n" \
              f"Sistema Operativo: {sistema_operativo}"

    return mensaje

def obtener_campos_metadatos(metadatos):
    campos = {}
    for linea in metadatos.split('\n'):
        if ':' in linea:
            clave, valor = [parte.strip() for parte in linea.split(':', 1)]
            campos[clave] = valor
    return campos

def calcular_diferencia_metadatos(metadatos_local, metadatos_remoto):
    campos_local = obtener_campos_metadatos(metadatos_local)
    campos_remoto = obtener_campos_metadatos(metadatos_remoto)

    diferencia = {}
    for clave, valor_local in campos_local.items():
        if clave in campos_remoto:
            valor_remoto = campos_remoto[clave]
            if valor_local != valor_remoto:
                diferencia[clave] = (valor_local, valor_remoto)

    if diferencia:
        diferencia_str = "Diferencia de Metadatos:\n"
        for clave, valores in diferencia.items():
            diferencia_str += f"{clave}:\n  Local: {valores[0]}\n  Remoto: {valores[1]}\n"
        return diferencia_str
    else:
        return "No hay diferencia en los metadatos."


# Variable para controlar si se debe monitorear el uso de la CPU
monitorear_cpu = False

def monitorear_uso_cpu():
    
    global monitorear_cpu

    while True:
        if monitorear_cpu:
            porcentaje_cpu = obtener_rendimiento_cpu()
            with print_lock:
                print(f'Uso actual de CPU: {porcentaje_cpu}%')

            if porcentaje_cpu > 40:
                enviar_correo('Alerta de Uso de CPU', f'El uso del CPU ha excedido el 40% ({porcentaje_cpu}%)')

            # Reinicia la variable para que vuelva a monitorear si es necesario
            monitorear_cpu = False

        time.sleep(1)  # Esperar 1 segundo antes de verificar nuevamente

if __name__ == "__main__":
    # Configuración del cliente MQTT
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect("broker.hivemq.com", 1883, 60)  # Cambia por tu broker o utiliza un broker local

    # Inicia un hilo para la recepción de mensajes MQTT
    mqtt_thread = threading.Thread(target=recibir_mensajes, args=(client,))
    mqtt_thread.start()

    # Inicia un hilo para monitorear el uso de la CPU
    cpu_monitor_thread = threading.Thread(target=monitorear_uso_cpu)
    cpu_monitor_thread.start()
try:
    while True:
        input("Presiona Enter para obtener información del sistema:\n")
        metadatos_local = obtener_metadatos()
        client.publish("metadatos", metadatos_local)  # Publica metadatos local en el tópico "metadatos"

        # Simulación de recepción de metadatos remotos desde otro equipo (cámbialo según tus necesidades)
        metadatos_remoto = f"Rendimiento CPU (%): {80}\nRendimiento de memoria: {60}\nTasa de Transferencia - Enviados (bytes/segundo): {500}\nTasa de Transferencia - Recibidos (bytes/segundo): {300}\nSistema Operativo: Windows"

        # Calcula la diferencia de metadatos
        diferencia_metadatos = calcular_diferencia_metadatos(metadatos_local, metadatos_remoto)

        # Verifica si hay alguna diferencia antes de proceder
        if diferencia_metadatos:
            # Muestra los rendimientos y la diferencia de metadatos en pantalla
            with print_lock:
                # Pregunta al usuario a qué tópico quiere enviar la diferencia de metadatos
                tópico_destino = input("\nIngrese el tópico de destino para la diferencia de metadatos:\n")

            # Publica la diferencia de metadatos en el tópico especificado por el usuario
            client.publish(tópico_destino, diferencia_metadatos)
        else:
            with print_lock:
                print("No hay diferencia en los metadatos.")

        # Pregunta al usuario si desea monitorear el uso de la CPU
        respuesta = input("¿Desea monitorear el uso de la CPU? (Sí/No): ").lower()
        if respuesta == "si":
            # Establece la variable para iniciar el monitoreo
            monitorear_cpu = True

        # Espera un poco para que el otro sistema también publique sus metadatos
        time.sleep(1)

except KeyboardInterrupt:
    # Desconectar al recibir una interrupción del teclado (Ctrl+C)
    client.disconnect()
    client.loop_stop()
    mqtt_thread.join()  # Espera a que el hilo de MQTT termine
    cpu_monitor_thread.join()  # Espera a que el hilo de monitoreo termine