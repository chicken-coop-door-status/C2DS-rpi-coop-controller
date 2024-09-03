import serial
import time
import logging

class ModemInitializer:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200, max_attempts=10, pause_seconds=30):
        self.port = port
        self.baudrate = baudrate
        self.max_attempts = max_attempts
        self.pause_seconds = pause_seconds
        self.logger = logging.getLogger('ModemInitializer')

    def connect_ecm(self):
        """Send AT#ECM=1,0 command to the modem and wait for OK response."""
        try:
            with serial.Serial(self.port, self.baudrate, timeout=10) as modem:
                for attempt in range(1, self.max_attempts + 1):
                    self.logger.info(f"Attempt {attempt}: Sending AT#ECM=1,0")
                    modem.write(b'AT#ECM=1,0\r\n')
                    response = modem.read_until(b'OK\r\n')

                    if b'OK' in response:
                        self.logger.info("Modem initialization successful.")
                        return True

                    self.logger.warning("AT command failed, retrying in %d seconds...", self.pause_seconds)
                    time.sleep(self.pause_seconds)

        except serial.SerialException as e:
            self.logger.error(f"Serial error: {e}")
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")

        self.logger.error("Modem initialization failed after %d attempts", self.max_attempts)
        return False

# Usage example at the top of your main controller script
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    modem_initializer = ModemInitializer()
    if modem_initializer.connect_ecm():
        # Proceed with the rest of the script only if modem initialization is successful
        main()
    else:
        logging.error("Cannot proceed without modem initialization. Exiting.")
