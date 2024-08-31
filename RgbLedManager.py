import RPi.GPIO as GPIO
import threading
import time


class RgbLedManager:
    LED_STATE_SOLID = 'SOLID'
    LED_STATE_BLINK = 'BLINK'
    LED_STATE_PULSE = 'PULSE'

    def __init__(self, red_pin, green_pin, blue_pin):
        self.red_pin = red_pin
        self.green_pin = green_pin
        self.blue_pin = blue_pin
        self.led_state = None
        self.blink_pulse_thread = None
        self.interval = 0
        self.running = False

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.red_pin, GPIO.OUT)
        GPIO.setup(self.green_pin, GPIO.OUT)
        GPIO.setup(self.blue_pin, GPIO.OUT)

        self.red_pwm = GPIO.PWM(self.red_pin, 1000)
        self.green_pwm = GPIO.PWM(self.green_pin, 1000)
        self.blue_pwm = GPIO.PWM(self.blue_pin, 1000)

        self.red_pwm.start(0)
        self.green_pwm.start(0)
        self.blue_pwm.start(0)

    def set_color(self, red, green, blue):
        self.red_pwm.ChangeDutyCycle(red / 8192 * 100)
        self.green_pwm.ChangeDutyCycle(green / 8192 * 100)
        self.blue_pwm.ChangeDutyCycle(blue / 8192 * 100)

    def set_led_named_color(self, color_state):
        color_lookup_table = {
            "LED_OFF": (0, 0, 0, self.LED_STATE_SOLID, 0),
            "LED_RED": (8192, 0, 0, self.LED_STATE_SOLID, 0),
            "LED_GREEN": (0, 8192, 0, self.LED_STATE_SOLID, 0),
            "LED_BLUE": (0, 0, 8192, self.LED_STATE_SOLID, 0),
            "LED_YELLOW": (8192, 8192, 0, self.LED_STATE_SOLID, 0),
            "LED_CYAN": (0, 8192, 8192, self.LED_STATE_SOLID, 0),
            "LED_MAGENTA": (8192, 0, 8192, self.LED_STATE_SOLID, 0),
            "LED_WHITE": (8192, 8192, 8192, self.LED_STATE_SOLID, 0),
            "LED_FLASHING_RED": (8192, 0, 0, self.LED_STATE_BLINK, 500),
            "LED_FLASHING_GREEN": (0, 8192, 0, self.LED_STATE_BLINK, 500),
            "LED_FLASHING_BLUE": (0, 0, 8192, self.LED_STATE_BLINK, 500),
            "LED_FLASHING_YELLOW": (8192, 8192, 0, self.LED_STATE_BLINK, 500),
            "LED_FLASHING_CYAN": (0, 8192, 8192, self.LED_STATE_BLINK, 500),
            "LED_FLASHING_MAGENTA": (8192, 0, 8192, self.LED_STATE_BLINK, 500),
            "LED_FLASHING_WHITE": (8192, 8192, 8192, self.LED_STATE_BLINK, 500),
            "LED_PULSE_RED": (8192, 0, 0, self.LED_STATE_PULSE, 10),
            "LED_PULSE_GREEN": (0, 8192, 0, self.LED_STATE_PULSE, 10),
            "LED_PULSE_BLUE": (0, 0, 8192, self.LED_STATE_PULSE, 10),
            "LED_PULSE_YELLOW": (8192, 8192, 0, self.LED_STATE_PULSE, 10),
            "LED_PULSE_CYAN": (0, 8192, 8192, self.LED_STATE_PULSE, 10),
            "LED_PULSE_MAGENTA": (8192, 0, 8192, self.LED_STATE_PULSE, 10),
            "LED_PULSE_WHITE": (8192, 8192, 8192, self.LED_STATE_PULSE, 10),
        }

        if color_state in color_lookup_table:
            red, green, blue, state, interval = color_lookup_table[color_state]
            self.set_led_enumerated_values(red, green, blue, state, interval)
        else:
            print(f"Color state '{color_state}' not found in lookup table")

    def set_led_enumerated_values(self, red, green, blue, state, interval):
        self.led_state = state
        self.interval = interval

        if self.blink_pulse_thread is not None:
            self.running = False
            self.blink_pulse_thread.join()

        if state == self.LED_STATE_SOLID:
            self.set_color(red, green, blue)
        elif state == self.LED_STATE_BLINK:
            self.running = True
            self.blink_pulse_thread = threading.Thread(target=self.blink_task, args=(red, green, blue))
            self.blink_pulse_thread.start()
        elif state == self.LED_STATE_PULSE:
            self.running = True
            self.blink_pulse_thread = threading.Thread(target=self.pulse_task, args=(red, green, blue))
            self.blink_pulse_thread.start()
        else:
            print("Unknown LED state!")

    def blink_task(self, red, green, blue):
        while self.running:
            self.set_color(red, green, blue)
            time.sleep(self.interval / 1000.0)
            self.set_color(0, 0, 0)
            time.sleep(self.interval / 1000.0)

    def pulse_task(self, red, green, blue):
        while self.running:
            for i in range(0, red, self.interval):
                self.set_color(i, i * green // red, i * blue // red)
                time.sleep(self.interval / 1000.0)
            time.sleep(0.01)
            for i in range(red, 0, -self.interval):
                self.set_color(i, i * green // red, i * blue // red)
                time.sleep(self.interval / 1000.0)
            time.sleep(0.01)

    def stop(self):
        self.running = False
        if self.blink_pulse_thread is not None:
            self.blink_pulse_thread.join()

    def cleanup(self):
        self.stop()
        self.red_pwm.stop()
        self.green_pwm.stop()
        self.blue_pwm.stop()
        GPIO.cleanup()


# Example usage:
# led_manager = RgbLedManager(red_pin=17, green_pin=27, blue_pin=22)
# led_manager.set_led_named_color("LED_BLINK_RED")
# time.sleep(5)
# led_manager.cleanup()
