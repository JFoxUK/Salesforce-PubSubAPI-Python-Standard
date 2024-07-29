import grpc
import requests
import threading
import io
import pubsub_api_pb2 as pb2
import pubsub_api_pb2_grpc as pb2_grpc
import avro.schema
import avro.io
import time
import certifi
import json
import logging
from datetime import datetime, timedelta
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from colorama import Fore, Style, init
import getpass  # For securely entering passwords

# Initialize colorama
init(autoreset=True)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Ask the user for configuration details
debug_choice = input("Debug all events? (Yes/No): ").strip().lower()
debug_all = debug_choice in ['yes', 'true', 'y', 't']

consumer_key = input("Enter the consumer key: ").strip()
org_id = input("Enter the organization ID: ").strip()
username = input("Enter the username: ").strip()
private_key_path = input("Enter the path to your private key (PEM file): ").strip()
private_key_passphrase = getpass.getpass("Enter the passphrase for the private key: ").strip().encode()

mysubtopic = input("Enter the subscription topic (e.g., /event/MobileEnforcedPolicyEvent): ").strip()
num_requested = int(input("Enter the number of events to retrieve at a time: ").strip())
replay_preset_choice = input("Enter the replay preset (LATEST, EARLIEST, CUSTOM): ").strip().upper()

# Map user input to gRPC ReplayPreset values
replay_preset_map = {
    "LATEST": pb2.ReplayPreset.LATEST,
    "EARLIEST": pb2.ReplayPreset.EARLIEST,
    "CUSTOM": pb2.ReplayPreset.CUSTOM,
}
replay_preset = replay_preset_map.get(replay_preset_choice, pb2.ReplayPreset.LATEST)

# Prompt for replay ID if CUSTOM preset is chosen
replay_id = None
if replay_preset == pb2.ReplayPreset.CUSTOM:
    replay_id_input = input("Enter the replay ID (in hex format)(You are entering the last recieved Id you saw, this will give you all events after that Id): ").strip()
    replay_id = bytes.fromhex(replay_id_input) if replay_id_input else None

# Initialize semaphore
semaphore = threading.Semaphore(1)

# Read and decrypt the private key
with open(private_key_path, 'rb') as key_file:
    private_key = serialization.load_pem_private_key(
        key_file.read(),
        password=private_key_passphrase,
        backend=default_backend()
    )

# Convert the private key to PEM format
pem_private_key = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.TraditionalOpenSSL,
    encryption_algorithm=serialization.NoEncryption()
)

# Create the JWT token
jwt_payload = {
    'iss': consumer_key,
    'sub': username,
    'aud': 'https://test.salesforce.com',  # Adjust to match your Salesforce environment
    'exp': int(time.time()) + 300,  # Token expiration time
}

jwt_token = jwt.encode(
    jwt_payload,
    pem_private_key,
    algorithm='RS256'
)

# URL to request the access token
url = 'https://test.salesforce.com/services/oauth2/token'
data = {
    'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
    'assertion': jwt_token
}

# Request the access token
response = requests.post(url, data=data)
response_json = response.json()

if response.status_code != 200:
    raise Exception(f"Error obtaining access token: {response_json.get('error_description', 'No error description')}")

access_token = response_json['access_token']
instance_url = response_json['instance_url']

# Print the access token and instance URL for debugging purposes
print(f"Access Token: {access_token}")
print(f"Instance URL: {instance_url}")

# Define authentication metadata for gRPC calls
authmetadata = (
    ('accesstoken', access_token),
    ('instanceurl', instance_url),
    ('tenantid', org_id)  # Replace with your actual Org ID if different
)

# Read SSL certificates for secure gRPC connections
with open(certifi.where(), 'rb') as f:
    creds = grpc.ssl_channel_credentials(f.read())

# Establish a secure channel with the Salesforce Pub/Sub API server
with grpc.secure_channel('api.pubsub.salesforce.com:7443', creds) as channel:
    # Create a stub for interacting with the Pub/Sub API
    stub = pb2_grpc.PubSubStub(channel)

    # Define a generator function for fetching requests from a topic
    def fetchReqStream(topic):
        while True:
            semaphore.acquire()
            replay_id_bytes = replay_id if replay_id and replay_preset == pb2.ReplayPreset.CUSTOM else b''
            if isinstance(replay_id_bytes, str):
                replay_id_bytes = bytes.fromhex(replay_id_bytes)
            
            yield pb2.FetchRequest(
                topic_name=topic,
                replay_preset=replay_preset,  # User-selected replay preset
                num_requested=num_requested,  # User-specified number of events to request at a time
                replay_id=replay_id_bytes
            )


    # Function to decode Avro payloads
    def decode(schema, payload):
        schema = avro.schema.parse(schema)
        buf = io.BytesIO(payload)
        decoder = avro.io.BinaryDecoder(buf)
        reader = avro.io.DatumReader(schema)
        ret = reader.read(decoder)
        return ret

    # Subscribe to the specified topic
    logging.info(f'Subscribing to {mysubtopic}')
    substream = stub.Subscribe(fetchReqStream(mysubtopic), metadata=authmetadata)
    
    # Process events from the subscription
    for event in substream:
        if event.events:
            semaphore.release()
            logging.info(f"Number of events received: {len(event.events)}")
            
            # Accessing the first event's payload and schema
            event_data = event.events[0]
            payloadbytes = event_data.event.payload
            schemaid = event_data.event.schema_id

            # Access the replay ID
            replay_id = event_data.replay_id.hex()
            logging.info(f"Replay ID: {replay_id}")

            # Decode the payload
            schema = stub.GetSchema(pb2.SchemaRequest(schema_id=schemaid), metadata=authmetadata).schema_json
            decoded = decode(schema, payloadbytes)
            
            # Parse and pretty-print the PolicyResults field
            if 'PolicyResults' in decoded:
                try:
                    policy_results = json.loads(decoded['PolicyResults'])
                    decoded['PolicyResults'] = policy_results

                    # Separate log for policy violations
                    violated_policies = []
                    
                    for policy in policy_results:
                        if policy.get('passed') == 'false':
                            violated_policies.append(policy)
                            logging.warning(f"{Fore.RED}*** Policy Violation ***\n{json.dumps(policy, indent=4)}{Style.RESET_ALL}\n")
                    
                    if violated_policies:
                        logging.debug(f"Violated Policies:\n{json.dumps(violated_policies, indent=4)}")
                    
                    # Debug all or only policy violations
                    if debug_all or violated_policies:
                        logging.info(f"Received Event:\n{json.dumps(decoded, indent=4)}")
                except json.JSONDecodeError as e:
                    logging.error(f"Error parsing PolicyResults: {e}")
            else:
                # In case of no PolicyResults but debug_all is True
                if debug_all:
                    logging.info(f"Received Event:\n{json.dumps(decoded, indent=4)}")
        else:
            logging.info(f"[{datetime.now().strftime('%b %d, %Y %I:%M%p %Z')}] The subscription is active.")
