# Email Delivery Time Monitor

A Python-based monitoring solution that measures email delivery time between Office 365 and Gmail, with integration for Zabbix monitoring and Grafana visualization.

## Features

- **Automated Email Testing**: Sends test emails from Office 365 to Gmail every 60 seconds
- **Delivery Time Measurement**: Accurately measures email delivery time
- **Zabbix Integration**: Sends metrics to Zabbix for monitoring and alerting
- **Comprehensive Logging**: Detailed logging with rotation
- **Error Handling**: Robust error handling with retry mechanisms
- **Configurable**: Easy configuration via JSON file

## Prerequisites

- Python 3.7 or higher
- Office 365 account with API access
- Gmail account with API access
- Zabbix server (optional, for monitoring integration)

## Installation

### Option 1: Docker Deployment (Recommended)

For containerized deployment on Portainer or any Docker host:

1. **Quick start with Docker Compose**:
   ```bash
   # Copy environment template
   cp .env.template .env
   # Edit .env with your credentials
   
   # Deploy with Docker Compose
   docker-compose up -d
   ```

2. **Or use the management script**:
   ```bash
   chmod +x docker-manage.sh
   ./docker-manage.sh start
   ```

See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for detailed Docker setup instructions.

### Option 2: Traditional Python Installation

For running directly on Windows:

1. **Clone or download the project files**
   ```powershell
   cd C:\Users\Jrd\Documents\emaildeliverytime
   ```

2. **Install Python dependencies**
   ```powershell
   pip install -r requirements.txt
   ```

## Configuration

### 1. Office 365 Setup

You need to register an application in Azure AD to get API access:

1. Go to [Azure Portal](https://portal.azure.com)
2. Navigate to **Azure Active Directory** > **App registrations**
3. Click **New registration**
4. Name your app (e.g., "Email Delivery Monitor")
5. Select **Accounts in this organizational directory only**
6. Click **Register**

After registration:
1. Note down the **Application (client) ID** and **Directory (tenant) ID**
2. Go to **Certificates & secrets** > **New client secret**
3. Create a new secret and note down the **Value**
4. Go to **API permissions** > **Add a permission**
5. Select **Microsoft Graph** > **Application permissions**
6. Add **Mail.Send** permission
7. Click **Grant admin consent**

### 2. Gmail Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the **Gmail API**
4. Go to **Credentials** > **Create Credentials** > **OAuth client ID**
5. Select **Desktop application**
6. Download the credentials JSON file and save as `gmail_credentials.json`

### 3. Configuration File

Edit `config.json` with your settings:

```json
{
    "office365": {
        "tenant_id": "your-tenant-id-here",
        "client_id": "your-client-id-here", 
        "client_secret": "your-client-secret-here",
        "sender_email": "sender@yourdomain.com"
    },
    "gmail": {
        "credentials_file": "gmail_credentials.json",
        "token_file": "gmail_token.json",
        "recipient_email": "recipient@gmail.com"
    },
    "monitoring": {
        "test_interval_seconds": 60,
        "timeout_seconds": 300,
        "max_retries": 3,
        "subject_prefix": "Email Delivery Test"
    },
    "zabbix": {
        "enabled": true,
        "server": "your-zabbix-server.com",
        "port": 10051,
        "host": "email-monitor"
    }
}
```

## Usage

### Running a Single Test
```powershell
python email_delivery_monitor.py --test
```

### Starting Continuous Monitoring
```powershell
python email_delivery_monitor.py
```

The monitor will:
1. Send a test email every 60 seconds (configurable)
2. Monitor Gmail for email arrival
3. Calculate delivery time
4. Send metrics to Zabbix
5. Log all activities

### Running as a Windows Service

To run continuously, you can:

1. **Use Task Scheduler**:
   - Open Task Scheduler
   - Create Basic Task
   - Set trigger to "At startup"
   - Set action to start your Python script
   - Configure to run whether user is logged on or not

2. **Use NSSM (Non-Sucking Service Manager)**:
   ```powershell
   # Download NSSM from https://nssm.cc/
   nssm install EmailDeliveryMonitor
   # Set path to python.exe and your script
   nssm set EmailDeliveryMonitor Application "C:\Python39\python.exe"
   nssm set EmailDeliveryMonitor AppParameters "C:\Users\Jrd\Documents\emaildeliverytime\email_delivery_monitor.py"
   nssm set EmailDeliveryMonitor AppDirectory "C:\Users\Jrd\Documents\emaildeliverytime"
   nssm start EmailDeliveryMonitor
   ```

## Zabbix Integration

### Zabbix Items

The monitor sends these metrics to Zabbix:

1. **email.delivery.time** - Delivery time in seconds (float)
2. **email.delivery.success** - Success flag (1 = success, 0 = failure)

### Zabbix Configuration

1. **Create Host**:
   - Host name: `email-monitor` (must match config)
   - Groups: Create a group like "Email Monitoring"

2. **Create Items**:

   **Delivery Time Item**:
   - Name: Email Delivery Time
   - Key: email.delivery.time
   - Type: Zabbix trapper
   - Value type: Numeric (float)
   - Units: s

   **Success Rate Item**:
   - Name: Email Delivery Success
   - Key: email.delivery.success  
   - Type: Zabbix trapper
   - Value type: Numeric (unsigned)

3. **Create Triggers**:

   **High Delivery Time**:
   ```
   {email-monitor:email.delivery.time.last()}>30
   ```

   **Delivery Failure**:
   ```
   {email-monitor:email.delivery.success.last()}=0
   ```

   **No Data**:
   ```
   {email-monitor:email.delivery.time.nodata(300)}=1
   ```

### Grafana Dashboard

Create a Grafana dashboard with these panels:

1. **Delivery Time Graph**:
   - Query: `email.delivery.time`
   - Visualization: Time series
   - Y-axis: Seconds

2. **Success Rate**:
   - Query: `email.delivery.success`
   - Visualization: Stat
   - Show as percentage over time

3. **Average Delivery Time**:
   - Query: `avg(email.delivery.time)`
   - Visualization: Stat
   - Time range: Last 24h

## Troubleshooting

### Common Issues

1. **Office 365 Authentication Errors**:
   - Verify tenant ID, client ID, and client secret
   - Ensure Mail.Send permission is granted and admin consented
   - Check if conditional access policies block the app

2. **Gmail API Errors**:
   - Ensure Gmail API is enabled in Google Cloud Console
   - Verify OAuth consent screen is configured
   - Check if gmail_credentials.json is valid
   - Run the script interactively first to complete OAuth flow

3. **Zabbix Connection Issues**:
   - Verify Zabbix server hostname and port
   - Ensure host exists in Zabbix with correct name
   - Check firewall rules for port 10051

4. **Email Not Received**:
   - Check spam/junk folders
   - Verify email addresses are correct
   - Check Office 365 and Gmail service status

### Logs

Check the log file `email_delivery_monitor.log` for detailed information about:
- Email sending attempts
- Gmail API responses
- Delivery time calculations
- Zabbix communication
- Errors and warnings

### Testing

1. **Test Office 365 Connection**:
   ```powershell
   python -c "from email_delivery_monitor import EmailDeliveryMonitor; m = EmailDeliveryMonitor(); print('Token:', m._get_office365_token()[:20] if m._get_office365_token() else 'Failed')"
   ```

2. **Test Gmail Connection**:
   ```powershell
   python -c "from email_delivery_monitor import EmailDeliveryMonitor; m = EmailDeliveryMonitor(); print('Gmail setup:', m._setup_gmail_service())"
   ```

3. **Test Single Email**:
   ```powershell
   python email_delivery_monitor.py --test
   ```

## Security Considerations

- Store credentials securely and restrict file permissions
- Use dedicated service accounts for API access
- Regularly rotate client secrets
- Monitor for unusual API usage
- Consider using Azure Key Vault for production deployments

## License

This project is provided as-is for monitoring purposes. Ensure compliance with your organization's email and API usage policies.
