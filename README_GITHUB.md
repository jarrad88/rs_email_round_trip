# Email Delivery Round Trip Monitor

[![Build and Push Docker Image](https://github.com/jarrad88/rs_email_round_trip/actions/workflows/docker-build.yml/badge.svg)](https://github.com/jarrad88/rs_email_round_trip/actions/workflows/docker-build.yml)
[![Docker Image](https://ghcr.io/jarrad88/rs_email_round_trip:latest)](https://github.com/jarrad88/rs_email_round_trip/pkgs/container/rs_email_round_trip)

A containerized email delivery time monitoring solution that measures round-trip email delivery between Office 365 and Gmail, with integrated Zabbix monitoring for RMM environments.

## 🚀 Quick Start with Portainer

1. **Create new stack** in Portainer
2. **Use Git repository**: `https://github.com/jarrad88/rs_email_round_trip.git`
3. **Compose file**: `portainer-stack.yml` 
4. **Configure environment variables** (see below)
5. **Deploy!**

## 📊 Features

- **Automated Testing**: Sends test emails every 60 seconds (configurable)
- **Precise Timing**: Measures actual email delivery time via header parsing  
- **Zabbix Integration**: Sends metrics directly to Zabbix server
- **Container Ready**: Optimized for Docker/Portainer deployment
- **Production Ready**: Health checks, logging, resource limits
- **Easy Management**: Web-based monitoring via Portainer

## ⚙️ Required Environment Variables

```env
OFFICE365_TENANT_ID=your-azure-tenant-id
OFFICE365_CLIENT_ID=your-app-client-id  
OFFICE365_CLIENT_SECRET=your-app-client-secret
OFFICE365_SENDER_EMAIL=sender@yourdomain.com
GMAIL_RECIPIENT_EMAIL=recipient@gmail.com
ZABBIX_SERVER=your-zabbix-server.com
```

## 📈 Monitoring Metrics

- **email.delivery.time** - Delivery time in seconds
- **email.delivery.success** - Success/failure flag
- **Comprehensive logging** with rotation
- **Health checks** and status monitoring

## 🔧 Setup Requirements

### Office 365 Setup
1. Register app in Azure AD
2. Grant **Mail.Send** permission  
3. Generate client secret
4. Get tenant and client IDs

### Gmail Setup  
1. Enable Gmail API in Google Cloud Console
2. Create OAuth 2.0 credentials
3. Download credentials JSON
4. Complete initial OAuth flow

### Zabbix Integration
- Import provided Zabbix template
- Create host with name matching `ZABBIX_HOST` variable
- Configure triggers and alerts

## 📋 Documentation

- **[PORTAINER_DEPLOYMENT.md](PORTAINER_DEPLOYMENT.md)** - Complete Portainer setup guide
- **[DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)** - Docker deployment options  
- **[ZABBIX_SETUP.md](ZABBIX_SETUP.md)** - Zabbix configuration guide
- **[README.md](README.md)** - Detailed setup and configuration

## 🐳 Container Image

The container image is automatically built and published to GitHub Container Registry:

```bash
docker pull ghcr.io/jarrad88/rs_email_round_trip:latest
```

## 🔄 Automatic Updates

The GitHub Actions workflow automatically:
- Builds Docker images on code changes
- Publishes to GitHub Container Registry  
- Supports multi-architecture (amd64, arm64)
- Includes basic testing

## 📞 Support

For RMM integration questions or issues:
- Check the documentation files
- Review container logs in Portainer
- Verify environment variable configuration
- Test individual components using manual test mode

Perfect for MSPs and IT teams needing reliable email delivery monitoring integrated with existing Zabbix/Grafana monitoring stacks.
