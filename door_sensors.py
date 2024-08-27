import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import json
import time
import logging
from threading import Timer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DoorSensors")

# GPIO pin definitions for the sensors
LEFT_SENSOR_GPIO = 17  # Use the correct GPIO pin number
RIGHT_SENSOR_GPIO = 27  # Use the correct GPIO pin number

# Enum to define door status
DOOR_STATUS_UNKNOWN = 0
DOOR_STATUS_OPEN = 1
DOOR_STATUS_CLOSED = 2
DOOR_STATUS_ERROR = 3

current_door_status = DOOR_STATUS_UNKNOWN
last_door_status = DOOR_STATUS_UNKNOWN

# MQTT client configuration
mqtt_client = mqtt.Client()
mqtt_topic = "coop/door/status"

# Timer for status check
status_timer = None


def init_sensors_gpio():
    """Initialize the GPIO pins for the sensors."""
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LEFT_SENSOR_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(RIGHT_SENSOR_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    GPIO.add_event_detect(LEFT_SENSOR_GPIO, GPIO.BOTH, callback=gpio_isr_handler, bouncetime=10)
    GPIO.add_event_detect(RIGHT_SENSOR_GPIO, GPIO.BOTH, callback=gpio_isr_handler, bouncetime=10)

    logger.info("Sensors initialized on GPIO pins %d and %d", LEFT_SENSOR_GPIO, RIGHT_SENSOR_GPIO)


def gpio_isr_handler(channel):
    """ISR handler for GPIO interrupts."""
    global current_door_status
    current_door_status = read_door_status()
    publish_door_status(current_door_status)


def read_door_status():
    """Read the door status from the sensors."""
    left_sensor_value = GPIO.input(LEFT_SENSOR_GPIO)
    right_sensor_value = GPIO.input(RIGHT_SENSOR_GPIO)

    if left_sensor_value == right_sensor_value:
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
    logger.info("Publishing door status: %s to topic %s", message, mqtt_topic)
    result = mqtt_client.publish(mqtt_topic, message)

    if result.rc != mqtt.MQTT_ERR_SUCCESS:
        logger.error("Failed to publish message to topic %s", mqtt_topic)
    else:
        logger.info("Publish successful to %s", mqtt_topic)


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


def on_connect(client, userdata, flags, rc):
    """Callback function for MQTT connection."""
    if rc == 0:
        logger.info("Connected to MQTT broker")
    else:
        logger.error("Failed to connect to MQTT broker, return code %d", rc)


def main():
    """Main function to initialize the system and start the MQTT loop."""
    global mqtt_client
    mqtt_client.on_connect = on_connect
    mqtt_client.connect("mqtt_broker_address", 1883, 60)  # Replace with actual broker address
    mqtt_client.loop_start()

    init_door_sensors(60)  # Check every 60 seconds

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        if status_timer is not None:
            status_timer.cancel()
        GPIO.cleanup()
        mqtt_client.loop_stop()
        mqtt_client.disconnect()


if __name__ == "__main__":
    main()
