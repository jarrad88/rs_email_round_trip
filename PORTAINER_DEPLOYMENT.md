# Portainer Deployment Guide - Email Delivery Monitor

This guide shows you how to deploy the Email Delivery Monitor in Portainer using the GitHub repository.

## 🚀 Quick Deployment in Portainer

### Step 1: Create New Stack

1. **Access Portainer**:
   - Open your Portainer web interface
   - Navigate to **Stacks** in the left sidebar
   - Click **+ Add stack**

2. **Stack Configuration**:
   - **Name**: `email-delivery-monitor`
   - **Build method**: Select **Repository**

3. **Repository Settings**:
   - **Repository URL**: `https://github.com/jarrad88/rs_email_round_trip.git`
   - **Repository reference**: `refs/heads/main` (or leave empty for default branch)
   - **Compose path**: `portainer-stack.yml`
   - **Authentication**: Toggle ON
   - **Username**: `jarrad88`
   - **Personal Access Token**: `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`

### Step 2: Configure Environment Variables

In the **Environment variables** section, add these variables:

```env
OFFICE365_TENANT_ID=your-azure-tenant-id
OFFICE365_CLIENT_ID=your-app-client-id  
OFFICE365_CLIENT_SECRET=your-app-client-secret
OFFICE365_SENDER_EMAIL=sender@yourdomain.com
GMAIL_RECIPIENT_EMAIL=recipient@gmail.com
ZABBIX_SERVER=your-zabbix-server.com
ZABBIX_PORT=10051
ZABBIX_HOST=email-monitor
TEST_INTERVAL=60
TIMEOUT_SECONDS=300
LOG_LEVEL=INFO
```

### Step 3: Deploy Stack

1. Click **Deploy the stack**
2. Wait for the deployment to complete
3. Check that the container is running in **Containers** section

## 📋 Required Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `OFFICE365_TENANT_ID` | ✅ | Your Azure AD tenant ID | `12345678-1234-1234-1234-123456789abc` |
| `OFFICE365_CLIENT_ID` | ✅ | App registration client ID | `87654321-4321-4321-4321-cba987654321` |
| `OFFICE365_CLIENT_SECRET` | ✅ | App registration client secret | `your-secret-value` |
| `OFFICE365_SENDER_EMAIL` | ✅ | Office 365 sender email | `monitoring@yourcompany.com` |
| `GMAIL_RECIPIENT_EMAIL` | ✅ | Gmail recipient email | `alerts@gmail.com` |
| `ZABBIX_SERVER` | ✅ | Zabbix server hostname/IP | `zabbix.yourcompany.com` |
| `ZABBIX_PORT` | ❌ | Zabbix server port | `10051` (default) |
| `ZABBIX_HOST` | ❌ | Host name in Zabbix | `email-monitor` (default) |
| `TEST_INTERVAL` | ❌ | Test interval in seconds | `60` (default) |
| `TIMEOUT_SECONDS` | ❌ | Email delivery timeout | `300` (default) |
| `LOG_LEVEL` | ❌ | Logging level | `INFO` (default) |

## 🔧 Post-Deployment Setup

### Upload Gmail Credentials

After deployment, you need to upload your Gmail API credentials:

1. **Access Container Files**:
   - Go to **Containers** → **email-delivery-monitor**
   - Click **Console** tab
   - Select **Connect** with `/bin/bash`

2. **Upload Credentials via Portainer**:
   - Go to **Volumes** → **email-monitor-credentials**
   - Click **Browse volume**
   - Upload your `gmail_credentials.json` file

3. **Alternative - Copy via Docker Command**:
   ```bash
   # From your Docker host
   docker cp gmail_credentials.json email-delivery-monitor:/app/credentials/
   ```

### Initial Gmail OAuth Setup

The first time the container runs, it needs to complete Gmail OAuth:

1. **Check Container Logs**:
   - Go to **Containers** → **email-delivery-monitor**
   - Click **Logs** tab
   - Look for OAuth URL in the logs

2. **Complete OAuth Flow**:
   - Copy the OAuth URL from logs
   - Open it in a browser
   - Grant permissions
   - Copy the authorization code

3. **Enter Code in Container**:
   - Go to **Console** tab in Portainer
   - Enter the authorization code when prompted
   - The `gmail_token.json` will be created automatically

## 📊 Monitoring the Deployment

### Container Health

1. **Container Status**:
   - Green icon = healthy and running
   - Check **Status** column in containers list
   - Health check runs every 60 seconds

2. **Resource Usage**:
   - View CPU and memory usage in container details
   - Default limits: 256MB RAM, 0.5 CPU cores

### Logs and Debugging

1. **View Logs**:
   - **Containers** → **email-delivery-monitor** → **Logs**
   - Toggle **Auto-refresh logs** for real-time monitoring
   - Use **Search** to filter specific events

2. **Common Log Messages**:
   ```
   INFO - Starting email delivery monitoring...
   INFO - Test email sent successfully with ID: abc12345
   INFO - Email abc12345 delivered in 15.43 seconds
   INFO - Successfully sent 2 metrics to Zabbix
   ```

3. **Error Troubleshooting**:
   - `Failed to acquire token`: Check Office 365 credentials
   - `Gmail API error`: Check Gmail credentials and OAuth
   - `Zabbix connection error`: Check Zabbix server settings

### Testing the Setup

1. **Manual Test**:
   - Go to **Console** tab
   - Run: `python email_delivery_monitor.py --test`
   - Check output for success/failure

2. **Check Zabbix Integration**:
   - Verify data in Zabbix **Latest data**
   - Look for `email.delivery.time` and `email.delivery.success` metrics

## 🔄 Updates and Maintenance

### Updating the Container

1. **Automatic Updates** (Recommended):
   - The GitHub Actions workflow automatically builds new images
   - In Portainer: **Stacks** → **email-delivery-monitor** → **⟳ Update**
   - Select **Re-pull image** to get latest version

2. **Manual Update**:
   - Go to **Images** section
   - Find `ghcr.io/jarrad88/rs_email_round_trip:latest`
   - Click **Pull latest**
   - Restart the stack

### Backup Configuration

1. **Export Stack**:
   - **Stacks** → **email-delivery-monitor** → **⬇ Download**
   - Saves the complete stack configuration

2. **Backup Volumes**:
   - **Volumes** → **email-monitor-logs** → **Export**
   - **Volumes** → **email-monitor-credentials** → **Export**

## 🚨 Troubleshooting

### Common Issues

1. **Container Won't Start**:
   ```bash
   # Check logs for specific error
   # Common causes:
   # - Missing required environment variables
   # - Invalid credentials
   # - Network connectivity issues
   ```

2. **Authentication Errors**:
   - **Office 365**: Verify tenant ID, client ID, and secret
   - **Gmail**: Re-run OAuth flow, check credentials file

3. **Network Issues**:
   - Ensure Portainer host can reach:
     - `login.microsoftonline.com` (Office 365)
     - `googleapis.com` (Gmail)
     - Your Zabbix server

4. **Permission Issues**:
   - Verify Office 365 app has **Mail.Send** permission
   - Ensure admin consent is granted
   - Check Gmail API is enabled

### Getting Support

1. **Container Logs**: Always check recent logs first
2. **Health Check**: Monitor health check status
3. **Test Mode**: Use manual test to isolate issues
4. **Environment**: Verify all environment variables are set correctly

## 🔐 Security Best Practices

### Environment Variables

- Never commit credentials to Git
- Use Portainer's environment variable management
- Consider using Docker secrets for sensitive data

### Network Security

- Limit container network access if possible
- Use HTTPS/TLS for all API communications
- Monitor unusual API usage patterns

### Access Control

- Restrict Portainer access to authorized personnel
- Use strong passwords for Portainer accounts
- Enable two-factor authentication where possible

## 📈 Scaling and High Availability

### Multiple Instances

To run multiple monitors (e.g., different email paths):

1. **Create Additional Stacks**:
   - Duplicate the stack with different names
   - Change `ZABBIX_HOST` for each instance
   - Use different `OFFICE365_SENDER_EMAIL` or `GMAIL_RECIPIENT_EMAIL`

2. **Resource Planning**:
   - Each instance uses ~128MB RAM
   - CPU usage is minimal during normal operation
   - Network bandwidth is low (API calls only)

### Load Distribution

- Deploy across multiple Portainer environments
- Use different geographic regions
- Implement different email routing paths

This deployment method provides a production-ready, easily manageable solution that integrates seamlessly with your existing Portainer infrastructure.
