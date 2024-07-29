# Salesforce-PubSubAPI-Python-Standard

This repository provides a Python client to subscribe to Salesforce Pub/Sub API events. It allows users to authenticate using a JWT and subscribe to a specified topic, logging event details and highlighting policy violations.

## Features
- Subscribe to Salesforce Pub/Sub API topics.
- Real-time event logging with detailed information.
- Highlight and debug policy violations.
- Customizable event fetch count and replay presets.

## Prerequisites

Before using this client, ensure you have the following:

1. **Salesforce Account**: Access to a Salesforce environment (e.g., sandbox or production).
2. **Connected App**: Create a connected app in Salesforce with OAuth settings configured.
3. **JWT Bearer Token Flow**: The connected app should be set up to use the JWT bearer token flow for authentication.
4. **Certificate**: A self-signed certificate uploaded to the connected app for secure communication.
5. **Python Environment**: Python 3.7+ installed on your system.

## Setup

### 1. Create a Connected App in Salesforce
- **Navigate to**: Setup > App Manager > New Connected App.
- **Basic Information**: Fill in the basic information (App Name, API Name, etc.).
- **API (Enable OAuth Settings)**:
  - Check "Enable OAuth Settings".
  - Set "Callback URL" to a valid URL (it won't be used but is required).
  - Select OAuth Scopes (e.g., `Full access (full)`).
  - **JWT Configuration**:
    - Generate a self-signed certificate.
    - Upload the certificate to the connected app.

### 2. Download and Configure the Client
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/JFoxUK/Salesforce-PubSubAPI-Python-Standard.git
   cd Salesforce-PubSubAPI-Python-Standard
   ```
2. **Install Dependencies:**:
   Ensure you have pip installed and then run:
   ```bash
   pip install -r requirements.txt
   ```
3. **Prepare the Private Key:**
   Ensure the private key file used in the JWT setup is available. The key should be in PEM format.

## Running the Client
### Command Line Interface
To run the client, simply execute the script:
```bash
python PubSubAPIClient.py
```
### Input Parameters
During execution, the script will prompt you to input the following details:

1. **Debug All Events?**: (Yes/No) - Choose whether to log all events or only those with policy violations.
2. **Consumer Key**: The client ID from the Salesforce connected app.
3. **Username**: The username of the Salesforce account.
4. **Private Key Path**: The file path to your PEM-formatted private key.
5. **Private Key Passphrase**: The passphrase used to protect your private key.
6. **Subscription Topic**: The topic to which you wish to subscribe (e.g., `/event/MobileEnforcedPolicyEvent`).
7. **Number of Events to Retrieve**: Specify the number of events to fetch per request.
8. **Replay Preset**: Choose how to retrieve events:
   - **LATEST**: Only new events since the last received.
   - **EARLIEST**: All available events from the beginning.
   - **CUSTOM**: Requires a specific replay ID to start from.

### Example Execution

```bash
python PubSubAPIClient.py
```
```bash
Debug all events? (Yes/No): Yes
Enter the consumer key: 3MVG9...
Enter the username: user@example.com
Enter the path to your private key (PEM file): ./key.pem
Enter the passphrase for the private key: *****
Enter the subscription topic (e.g., /event/MobileEnforcedPolicyEvent): /event/MobileEnforcedPolicyEvent
Enter the number of events to retrieve at a time: 10
Enter the replay preset (LATEST, EARLIEST, CUSTOM): LATEST
```

### Output
The client will output logs for each event received, highlighting policy violations in red if any exist. All received events and potential issues will be logged for further inspection. This is hard-coded and coloured for the '/event/MobileEnforcedPolicyEvent'. Edit the client to debug the event for your own use case. For any other event type, it should still debug but you will have unnecessary code.

### Troubleshooting
- **Authentication Issues**: Ensure that your consumer key, private key, and passphrase are correct. Check that your Salesforce connected app is configured for JWT authentication.
- **Event Retrieval**: If no events are being retrieved, verify the subscription topic and ensure that there are events being generated in Salesforce.

### Contributing
Contributions are welcome! Please submit a pull request or open an issue for any feature requests or bug reports.

### License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
