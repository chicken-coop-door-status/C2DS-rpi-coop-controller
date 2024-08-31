import RPi.GPIO as GPIO
import json
import time
import logging
from threading import Timer
from awscrt import mqtt
from awsiot import mqtt_connection_builder

# Replace with your endpoint and credentials
endpoint = "ay1nsbhuqfhzk-ats.iot.us-east-2.amazonaws.com"
cert_filepath = "/greengrass/v2/thingCert.crt"
key_filepath = "/greengrass/v2/privKey.key"
ca_filepath = "/greengrass/v2/rootCA.pem"
client_id = "coop-monitor"
topic = "farm/coop/door/status"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DoorSensors")

# GPIO pin definitions for the sensors
LEFT_SENSOR_GPIO = 18  
RIGHT_SENSOR_GPIO = 23 

# Enum to define door status
DOOR_STATUS_UNKNOWN = 0
DOOR_STATUS_OPEN = 1
DOOR_STATUS_CLOSED = 2
DOOR_STATUS_ERROR = 3

current_door_status = DOOR_STATUS_UNKNOWN
last_door_status = DOOR_STATUS_UNKNOWN


# Create MQTT connection
mqtt_connection = mqtt_connection_builder.mtls_from_path(
    endpoint=endpoint,
    cert_filepath=cert_filepath,
    pri_key_filepath=key_filepath,
    client_bootstrap=None,
    ca_filepath=ca_filepath,
    on_connection_interrupted=None,
    on_connection_resumed=None,
    client_id=client_id,
    clean_session=False,
    keep_alive_secs=30
)

def init_sensors_gpio():
    """Initialize the GPIO pins for the sensors."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LEFT_SENSOR_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(RIGHT_SENSOR_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    GPIO.add_event_detect(LEFT_SENSOR_GPIO, GPIO.BOTH, callback=gpio_isr_handler, bouncetime=10)
    GPIO.add_event_detect(RIGHT_SENSOR_GPIO, GPIO.BOTH, callback=gpio_isr_handler, bouncetime=10)

    logger.info("Sensors initialized on GPIO pins %d and %d", LEFT_SENSOR_GPIO, RIGHT_SENSOR_GPIO)


def gpio_isr_handler():
    """ISR handler for GPIO interrupts."""
    global current_door_status
    current_door_status = read_door_status()
    publish_door_status(current_door_status)


def read_door_status():
    """Read the door status from the sensors."""
    left_sensor_value = GPIO.input(LEFT_SENSOR_GPIO)
    right_sensor_value = GPIO.input(RIGHT_SENSOR_GPIO)

    if left_sensor_value == right_sensor_value:
        logger.error("Left/right sensor values match")
        return DOOR_STATUS_CLOSED if left_sensor_value else DOOR_STATUS_OPEN
    else:
        logger.error("Left and right sensor values do not match!")
        return DOOR_STATUS_ERROR


def publish_door_status(status):
    """Publish the door status to the specified MQTT topic."""
    status_str = {
        DOOR_STATUS_OPEN: "OPEN",
        DOOR_STATUS_CLOSED: "CLOSED",
        DOOR_STATUS_ERROR: "ERROR",
        DOOR_STATUS_UNKNOWN: "UNKNOWN"
    }.get(status, "UNKNOWN")

    message = json.dumps({"door": status_str})
    logger.info("Publishing door status: %s to topic %s", message, topic)
    mqtt_connection.publish(
        topic=topic,
        payload=message,
        qos=mqtt.QoS.AT_LEAST_ONCE
    )
    print("Message published!")

def status_timer_callback():
    """Timer callback function to read the door status and publish if it has changed."""
    global current_door_status, last_door_status
    logger.info("Timer callback - Checking door status and publishing to MQTT")
    current_door_status = read_door_status()
    if current_door_status != last_door_status:
        publish_door_status(current_door_status)
        last_door_status = current_door_status

def init_status_timer(transmit_interval_seconds):
    """Initialize the status timer."""
    global status_timer
    status_timer = Timer(transmit_interval_seconds, status_timer_callback)
    status_timer.start()
    logger.info("Status timer initialized with interval %d seconds", transmit_interval_seconds)

def init_door_sensors(transmit_interval_seconds):
    """Initialize the door sensors and the status timer."""
    init_sensors_gpio()
    init_status_timer(transmit_interval_seconds)

def main():
    """Main function to initialize the system and start the MQTT loop."""
    print("Connecting to {}...".format(endpoint))
    connect_future = mqtt_connection.connect()
    connect_future.result()
    print("Connected!")

    init_door_sensors(60)  # Check every 60 seconds

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        if status_timer is not None:
            print("Cancelling status timer!")
            status_timer.cancel()
        print("Disconnecting...")
        disconnect_future = mqtt_connection.disconnect()
        disconnect_future.result()
        print("Disconnected!")

if __name__ == "__main__":
    main()
