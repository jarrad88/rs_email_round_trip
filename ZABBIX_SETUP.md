# Zabbix Configuration for Email Delivery Monitor

This document provides step-by-step instructions for configuring Zabbix to monitor email delivery times.

## Import Template

1. **Import the Template**:
   - Go to Zabbix web interface
   - Navigate to **Configuration** > **Templates**
   - Click **Import**
   - Upload `zabbix_template.xml`
   - Click **Import**

## Create Host

1. **Add New Host**:
   - Go to **Configuration** > **Hosts**
   - Click **Create host**
   - Fill in details:
     - **Host name**: `email-monitor` (must match config.json)
     - **Visible name**: `Email Delivery Monitor`
     - **Groups**: Select "Email Monitoring" (created by template)
     - **Interfaces**: Add Agent interface (use 127.0.0.1 if running locally)

2. **Link Template**:
   - In the **Templates** tab
   - Click **Select** next to **Link new templates**
   - Choose "Email Delivery Monitor"
   - Click **Add**
   - Click **Add** to save the host

## Verify Configuration

1. **Check Items**:
   - Go to **Configuration** > **Hosts**
   - Click **Items** next to your host
   - Verify these items exist:
     - `email.delivery.time` - Email Delivery Time
     - `email.delivery.success` - Email Delivery Success Rate

2. **Check Triggers**:
   - Click **Triggers** next to your host
   - Verify these triggers exist:
     - Email delivery time is high (>30s)
     - Email delivery time is very high (>60s) 
     - Email delivery failed
     - No email delivery data received

## Manual Items Configuration (Alternative)

If you prefer to create items manually instead of using the template:

### Items

1. **Email Delivery Time**:
   ```
   Name: Email Delivery Time
   Type: Zabbix trapper
   Key: email.delivery.time
   Type of information: Numeric (float)
   Units: s
   History storage period: 7d
   Trend storage period: 90d
   ```

2. **Email Delivery Success**:
   ```
   Name: Email Delivery Success
   Type: Zabbix trapper  
   Key: email.delivery.success
   Type of information: Numeric (unsigned)
   History storage period: 7d
   Trend storage period: 90d
   ```

### Triggers

1. **High Delivery Time (Warning)**:
   ```
   Name: Email delivery time is high on {HOST.NAME}
   Expression: last(/email-monitor/email.delivery.time)>30
   Severity: Warning
   ```

2. **Very High Delivery Time (High)**:
   ```
   Name: Email delivery time is very high on {HOST.NAME}
   Expression: last(/email-monitor/email.delivery.time)>60
   Severity: High
   ```

3. **Delivery Failure (High)**:
   ```
   Name: Email delivery failed on {HOST.NAME}
   Expression: last(/email-monitor/email.delivery.success)=0
   Severity: High
   ```

4. **No Data (Warning)**:
   ```
   Name: No email delivery data received on {HOST.NAME}
   Expression: nodata(/email-monitor/email.delivery.time,300)=1
   Severity: Warning
   ```

## Testing the Configuration

1. **Run Test**:
   ```powershell
   python email_delivery_monitor.py --test
   ```

2. **Check Latest Data**:
   - Go to **Monitoring** > **Latest data**
   - Filter by host: `email-monitor`
   - Verify data is being received

3. **Test Triggers**:
   - Go to **Monitoring** > **Problems**
   - Check if any triggers are firing appropriately

## Grafana Integration

### Add Zabbix Data Source

1. **Configure Data Source**:
   ```
   Name: Zabbix
   Type: Zabbix
   URL: http://your-zabbix-server/api_jsonrpc.php
   Username: your-zabbix-username
   Password: your-zabbix-password
   ```

### Create Dashboard

1. **Delivery Time Panel**:
   ```
   Query: email.delivery.time
   Visualization: Time series
   Title: Email Delivery Time
   Y-Axis: Time (seconds)
   Thresholds: 30s (yellow), 60s (red)
   ```

2. **Success Rate Panel**:
   ```
   Query: email.delivery.success
   Visualization: Stat
   Title: Email Delivery Success Rate
   Value: Last value
   Unit: Percent (0-100)
   Color: Green (success), Red (failure)
   ```

3. **Average Delivery Time Panel**:
   ```
   Query: avg(email.delivery.time)
   Visualization: Stat  
   Title: Average Delivery Time (24h)
   Time Range: Last 24 hours
   Unit: Seconds
   ```

4. **Delivery Time Histogram**:
   ```
   Query: email.delivery.time
   Visualization: Histogram
   Title: Delivery Time Distribution
   Buckets: 0-5s, 5-10s, 10-30s, 30-60s, 60s+
   ```

## Alerting

### Zabbix Actions

1. **Create Action for Email Delivery Issues**:
   - Go to **Configuration** > **Actions** > **Trigger actions**
   - Click **Create action**
   - Name: "Email Delivery Alerts"
   - Conditions:
     - Trigger name contains "Email delivery"
     - Host group equals "Email Monitoring"
   - Operations:
     - Send message to admin users
     - Send to external alerting system (PagerDuty, Slack, etc.)

### Sample Alert Messages

**High Delivery Time**:
```
Subject: Email Delivery Time Alert - {HOST.NAME}
Message: 
Email delivery time is high on {HOST.NAME}
Current delivery time: {ITEM.LASTVALUE} seconds
Time: {EVENT.DATE} {EVENT.TIME}
```

**Delivery Failure**:
```
Subject: Email Delivery Failure - {HOST.NAME}  
Message:
Email delivery test failed on {HOST.NAME}  
Last successful delivery: {ITEM.LASTVALUE}
Time: {EVENT.DATE} {EVENT.TIME}
Please check email service status.
```

## Maintenance and Monitoring

### Regular Checks

1. **Weekly**:
   - Review delivery time trends
   - Check for any failed deliveries
   - Verify monitoring is running consistently

2. **Monthly**:
   - Review and adjust trigger thresholds if needed
   - Check disk space for log files
   - Update API credentials if necessary

### Troubleshooting

1. **No Data in Zabbix**:
   - Check if email_delivery_monitor.py is running
   - Verify Zabbix server/port in config.json
   - Check Zabbix server logs for connection issues

2. **False Alarms**:
   - Adjust trigger thresholds based on baseline performance
   - Consider time-of-day variations in email delivery
   - Add dependencies between triggers to reduce noise

3. **Missing Triggers**:
   - Verify trigger expressions match your host name
   - Check that host is linked to template correctly
   - Ensure items are receiving data regularly
