# Docker Deployment Guide for Email Delivery Monitor

This guide covers deploying the Email Delivery Monitor in Docker containers using Portainer.

## 🐳 Container Benefits

- **Isolation**: Runs in its own environment with dependencies
- **Scalability**: Easy to scale or replicate across environments  
- **Portability**: Runs consistently on any Docker-compatible system
- **Management**: Easy deployment and monitoring through Portainer
- **Resource Control**: Built-in resource limits and monitoring

## 📋 Prerequisites

- Docker host with Portainer installed
- Office 365 app registration (see main README.md)
- Gmail API credentials (see main README.md)
- Access to your Zabbix server from the Docker host

## 🚀 Quick Deployment in Portainer

### Method 1: Using Git Repository (Recommended)

1. **Create Stack in Portainer**:
   - Go to **Stacks** > **Add stack**
   - Name: `email-delivery-monitor`
   - Build method: **Repository**
   - Repository URL: `https://github.com/jarrad88/rs_email_round_trip.git`
   - Compose path: `portainer-stack.yml`
   - Authentication: Enable with GitHub token

2. **Configure Environment Variables**:
   ```env
   OFFICE365_TENANT_ID=your-tenant-id
   OFFICE365_CLIENT_ID=your-client-id
   OFFICE365_CLIENT_SECRET=your-client-secret
   OFFICE365_SENDER_EMAIL=sender@yourdomain.com
   GMAIL_RECIPIENT_EMAIL=recipient@gmail.com
   ZABBIX_SERVER=your-zabbix-server.com
   ZABBIX_PORT=10051
   ZABBIX_HOST=email-monitor
   TEST_INTERVAL=60
   TIMEOUT_SECONDS=300
   LOG_LEVEL=INFO
   ```

3. **Deploy**: Click **Deploy the stack**

### Method 2: Manual File Upload

1. **Upload Files to Portainer**:
   - Create new stack: `email-delivery-monitor`
   - Copy the `docker-compose.yml` content into the web editor
   - Or upload the compose file

2. **Create .env File**:
   - Copy `.env.template` to `.env`
   - Fill in your actual credentials and settings

3. **Deploy Stack**

### Method 3: Using Docker CLI

If you prefer command line:

```bash
# Clone or copy files to Docker host
git clone your-repo email-delivery-monitor
cd email-delivery-monitor

# Copy and configure environment
cp .env.template .env
# Edit .env with your settings

# Build and start
docker-compose up -d
```

## 📁 Volume Configuration

The container uses these volumes:

### Required Volumes

1. **Logs Volume**: `/app/logs`
   - Stores application logs
   - Rotated automatically
   - Mount to host for persistence

2. **Credentials Volume**: `/app/credentials`
   - Store Gmail API credentials
   - Secure storage for sensitive files
   - Mount as read-only if possible

### Setting up Credentials

1. **Gmail Credentials**:
   ```bash
   # Copy your Gmail credentials to the credentials volume
   docker cp gmail_credentials.json email-delivery-monitor:/app/credentials/
   ```

2. **Portainer File Manager**:
   - Use Portainer's file manager
   - Navigate to container volumes
   - Upload `gmail_credentials.json` to credentials volume

## 🔧 Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OFFICE365_TENANT_ID` | - | Azure AD tenant ID |
| `OFFICE365_CLIENT_ID` | - | App registration client ID |
| `OFFICE365_CLIENT_SECRET` | - | App registration client secret |
| `OFFICE365_SENDER_EMAIL` | - | Sender email address |
| `GMAIL_RECIPIENT_EMAIL` | - | Gmail recipient address |
| `ZABBIX_SERVER` | - | Zabbix server hostname/IP |
| `ZABBIX_PORT` | 10051 | Zabbix server port |
| `ZABBIX_HOST` | email-monitor | Host name in Zabbix |
| `TEST_INTERVAL` | 60 | Test interval in seconds |
| `TIMEOUT_SECONDS` | 300 | Email delivery timeout |
| `LOG_LEVEL` | INFO | Logging level |

### Resource Limits

Default limits in `docker-compose.yml`:
- **Memory**: 256MB limit, 128MB reservation
- **CPU**: 0.5 CPU limit, 0.1 CPU reservation

Adjust based on your needs:
```yaml
deploy:
  resources:
    limits:
      memory: 512M  # Increase if needed
      cpus: '1.0'
    reservations:
      memory: 256M
      cpus: '0.2'
```

## 📊 Monitoring the Container

### Portainer Dashboard

1. **Container Stats**:
   - Go to **Containers** > **email-delivery-monitor**
   - View CPU, memory, and network usage
   - Check container logs

2. **Health Checks**:
   - Built-in health check monitors log file creation
   - Shows as healthy/unhealthy in Portainer
   - Configure alerts for health check failures

### Log Monitoring

**View Logs in Portainer**:
- Container details > **Logs** tab
- Real-time log streaming
- Download logs for analysis

**Access Log Files**:
```bash
# View logs directly
docker exec email-delivery-monitor tail -f /app/logs/email_delivery_monitor.log

# Copy logs to host
docker cp email-delivery-monitor:/app/logs/email_delivery_monitor.log ./
```

### Container Shell Access

```bash
# Access container shell for debugging
docker exec -it email-delivery-monitor /bin/bash

# Run manual test
docker exec email-delivery-monitor python email_delivery_monitor.py --test
```

## 🔄 Updates and Maintenance

### Updating the Container

1. **Using Portainer**:
   - Go to **Stacks** > **email-delivery-monitor**
   - Click **Editor** tab
   - Modify configuration
   - Click **Update the stack**

2. **Rebuilding Image**:
   ```bash
   # Pull latest code
   git pull
   
   # Rebuild and restart
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

### Backup and Restore

**Backup**:
```bash
# Backup configuration and logs
docker cp email-delivery-monitor:/app/logs ./backup-logs
docker cp email-delivery-monitor:/app/credentials ./backup-credentials

# Export container configuration
docker inspect email-delivery-monitor > container-config.json
```

**Restore**:
```bash
# Restore to new container
docker cp ./backup-credentials email-delivery-monitor:/app/credentials
docker cp ./backup-logs email-delivery-monitor:/app/logs
```

## 🚨 Troubleshooting

### Common Issues

1. **Container Won't Start**:
   ```bash
   # Check logs
   docker logs email-delivery-monitor
   
   # Common causes:
   # - Missing environment variables
   # - Invalid credentials
   # - Network connectivity issues
   ```

2. **No Email Being Sent**:
   ```bash
   # Test Office 365 connection
   docker exec email-delivery-monitor python -c "
   from email_delivery_monitor import EmailDeliveryMonitor
   m = EmailDeliveryMonitor('/app/config.docker.json')
   print('Token acquired:', bool(m._get_office365_token()))
   "
   ```

3. **Gmail API Issues**:
   ```bash
   # Check credentials file
   docker exec email-delivery-monitor ls -la /app/credentials/
   
   # Test Gmail connection
   docker exec email-delivery-monitor python -c "
   from email_delivery_monitor import EmailDeliveryMonitor
   m = EmailDeliveryMonitor('/app/config.docker.json')
   print('Gmail setup:', m._setup_gmail_service())
   "
   ```

4. **Zabbix Connection Issues**:
   ```bash
   # Test network connectivity
   docker exec email-delivery-monitor ping your-zabbix-server.com
   
   # Test Zabbix port
   docker exec email-delivery-monitor nc -zv your-zabbix-server.com 10051
   ```

### Performance Tuning

**High Memory Usage**:
- Increase memory limits
- Check for memory leaks in logs
- Reduce log retention

**CPU Usage**:
- Increase test interval
- Optimize email parsing
- Use CPU limits appropriately

**Network Issues**:
- Check firewall rules
- Verify DNS resolution
- Test external connectivity

## 🔐 Security Considerations

### Container Security

1. **Non-Root User**: Container runs as non-root user
2. **Read-Only Volumes**: Mount credentials as read-only
3. **Network Isolation**: Use custom Docker networks
4. **Resource Limits**: Prevent resource exhaustion

### Credential Management

1. **Docker Secrets** (for Swarm):
   ```yaml
   secrets:
     office365_secret:
       external: true
   ```

2. **Environment File Security**:
   ```bash
   # Secure .env file
   chmod 600 .env
   chown root:root .env
   ```

3. **Credential Rotation**:
   - Regularly rotate API keys
   - Update container without downtime
   - Monitor for credential expiry

## 📈 Scaling and High Availability

### Multiple Instances

Run multiple instances for redundancy:
```yaml
services:
  email-monitor-1:
    # ... configuration
    environment:
      - ZABBIX_HOST=email-monitor-1
      
  email-monitor-2:
    # ... configuration  
    environment:
      - ZABBIX_HOST=email-monitor-2
```

### Load Balancing

Distribute monitoring across regions:
- Deploy containers in different data centers
- Use different email paths (Office 365 → Gmail vs Office 365 → Outlook)
- Aggregate metrics in Zabbix

### Disaster Recovery

- Backup container configurations
- Store credentials in secure vault
- Document recovery procedures
- Test failover scenarios

This Docker deployment provides a production-ready, scalable solution for email delivery monitoring that integrates seamlessly with your existing Portainer and Zabbix infrastructure.
