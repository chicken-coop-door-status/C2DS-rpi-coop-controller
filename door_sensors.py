import RPi.GPIO as GPIO
import json
import time
import logging
from threading import Timer
from awscrt import mqtt
from awsiot import mqtt_connection_builder
import RgbLedManager
from awsiot import mqtt5_client_builder
from LocalTimeLogger import setup_local_time_logger
from ModemInitializer import ModemInitializer 

# Replace with your endpoint and credentials
endpoint = "ay1nsbhuqfhzk-ats.iot.us-east-2.amazonaws.com"
cert_filepath = "/greengrass/v2/thingCert.crt"
key_filepath = "/greengrass/v2/privKey.key"
ca_filepath = "/greengrass/v2/rootCA.pem"
client_id = "coop-monitor"

MQTT_COOP_STATUS_TOPIC = "farm/coop/door/status"
MQTT_LED_COLOR_TOPIC = "farm/coop/led/color"

# Set up the logger
logger = setup_local_time_logger()

TIMEOUT = 100

# How often do we check door status?
SENSOR_CHECK_INTERVAL_SECONDS = 60 * 60 * 1  # One hour 

# GPIO pin definitions for the sensors
LEFT_SENSOR_GPIO = 18  
RIGHT_SENSOR_GPIO = 23 

# GPIO pins for RGB LED
RGB_LED_RED_GPIO = 21
RGB_LED_GREEN_GPIO = 20
RGB_LED_BLUE_GPIO = 16

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

led_manager = RgbLedManager.RgbLedManager(red_pin=RGB_LED_RED_GPIO, green_pin=RGB_LED_GREEN_GPIO, blue_pin=RGB_LED_BLUE_GPIO)

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
    logger.info(f'Read door status: {current_door_status}')
    publish_door_status(current_door_status)


def read_door_status():
    """Read the door status from the sensors, retrying up to 10 times if necessary."""
    max_attempts = 10
    attempt = 0

    while attempt < max_attempts:
        left_sensor_value = GPIO.input(LEFT_SENSOR_GPIO)
        right_sensor_value = GPIO.input(RIGHT_SENSOR_GPIO)

        if left_sensor_value == right_sensor_value:
            logger.info("Left/right sensor values match on attempt %d", attempt + 1)
            return DOOR_STATUS_CLOSED if left_sensor_value else DOOR_STATUS_OPEN
        else:
            logger.warning("Left and right sensor values do not match on attempt %d", attempt + 1)
            attempt += 1
            time.sleep(1)  # Pause for 1 second before trying again

    logger.error("Left and right sensor values did not match after %d attempts!", max_attempts)
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
    logger.info("Publishing door status: %s to topic %s", message, MQTT_COOP_STATUS_TOPIC)
    mqtt_connection.publish(
        topic=MQTT_COOP_STATUS_TOPIC,
        payload=message,
        qos=mqtt.QoS.AT_LEAST_ONCE
    )
    logger.info("Message published!")

def status_timer_callback():
    """Timer callback function to read the door status and publish if it has changed."""
    logger.info("Timer callback - Checking door status and publishing to MQTT")
    current_door_status = read_door_status()
    publish_door_status(current_door_status)
    # Restart the timer to keep it recurring
    init_status_timer(SENSOR_CHECK_INTERVAL_SECONDS)

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

def on_message_received(topic, payload, **kwargs):
    """Callback when a message is received from the MQTT broker."""
    try:
        message = json.loads(payload)
        color_name = message.get("LED")
        if color_name:
            logger.info("Received color command: %s", color_name)
            led_manager.set_led_named_color(color_name)
        else:
            logger.warning("No 'color' key in the received message payload")
    except json.JSONDecodeError as e:
        logger.error("Failed to decode JSON payload: %s", e)

def main():
    """Main function to initialize the system and start the MQTT loop."""
    logger.info("Connecting to {}...".format(endpoint))
    connect_future = mqtt_connection.connect()
    connect_future.result()
    logger.info("Connected!")

    logger.info("Subscribing to topic '{}'...".format(MQTT_LED_COLOR_TOPIC))
    subscribe_future, packet_id = mqtt_connection.subscribe(
        topic=MQTT_LED_COLOR_TOPIC,
        qos=mqtt.QoS.AT_LEAST_ONCE,
        callback=on_message_received
    )
    subscribe_future.result()
    logger.info("Subscribed successfully!")

    init_door_sensors(SENSOR_CHECK_INTERVAL_SECONDS)
    current_door_status = read_door_status()
    publish_door_status(current_door_status)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        if status_timer is not None:
            logger.info("Cancelling status timer!")
            status_timer.cancel()
        GPIO.cleanup()
        logger.info("Disconnecting...")
        disconnect_future = mqtt_connection.disconnect()
        disconnect_future.result()
        logger.info("Disconnected!")

if __name__ == "__main__":
    modem_initializer = ModemInitializer(port='/dev/ttyUSB2')
    if modem_initializer.connect_ecm():
        main()
    else:
        logger.error("Could not connect to ECM!")
