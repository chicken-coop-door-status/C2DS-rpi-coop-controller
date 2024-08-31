import json
from awscrt import mqtt
from awsiot import mqtt_connection_builder

# Replace with your endpoint and credentials
endpoint = "ay1nsbhuqfhzk-ats.iot.us-east-2.amazonaws.com"
cert_filepath = "/greengrass/v2/thingCert.crt"
key_filepath = "/greengrass/v2/privKey.key"
ca_filepath = "/greengrass/v2/rootCA.pem"
client_id = "test-app1"
topic = "farm/coop/door/status"
message = {"door": "OPEN"}

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

# Connect to AWS IoT
print("Connecting to {}...".format(endpoint))
connect_future = mqtt_connection.connect()
connect_future.result()
print("Connected!")

# Publish message to the topic
print("Publishing message to topic {}...".format(topic))
mqtt_connection.publish(
    topic=topic,
    payload=json.dumps(message),
    qos=mqtt.QoS.AT_LEAST_ONCE
)
print("Message published!")

# Disconnect
print("Disconnecting...")
disconnect_future = mqtt_connection.disconnect()
disconnect_future.result()
print("Disconnected!")

