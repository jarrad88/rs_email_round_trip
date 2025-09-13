#!/bin/bash

# Email Delivery Monitor Startup Script
# Handles environment variable validation and configuration

set -e

echo "=== Email Delivery Monitor Startup ==="
echo "Timestamp: $(date)"

# Function to check required environment variables
check_env_vars() {
    local missing_vars=()
    
    # Check required Office 365 variables
    [ -z "$OFFICE365_TENANT_ID" ] && missing_vars+=("OFFICE365_TENANT_ID")
    [ -z "$OFFICE365_CLIENT_ID" ] && missing_vars+=("OFFICE365_CLIENT_ID")
    [ -z "$OFFICE365_CLIENT_SECRET" ] && missing_vars+=("OFFICE365_CLIENT_SECRET")
    [ -z "$OFFICE365_SENDER_EMAIL" ] && missing_vars+=("OFFICE365_SENDER_EMAIL")
    [ -z "$GMAIL_RECIPIENT_EMAIL" ] && missing_vars+=("GMAIL_RECIPIENT_EMAIL")
    [ -z "$ZABBIX_SERVER" ] && missing_vars+=("ZABBIX_SERVER")
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo "❌ ERROR: Missing required environment variables:"
        printf '   - %s\n' "${missing_vars[@]}"
        echo ""
        echo "Please set these environment variables in your Portainer stack configuration."
        echo "Example:"
        echo "  - OFFICE365_TENANT_ID=your-tenant-id"
        echo "  - OFFICE365_CLIENT_ID=your-client-id"
        echo "  - OFFICE365_CLIENT_SECRET=your-client-secret"
        echo "  - OFFICE365_SENDER_EMAIL=email-monitor@yourdomain.com"
        echo "  - GMAIL_RECIPIENT_EMAIL=recipient@gmail.com"
        echo "  - ZABBIX_SERVER=your-zabbix-server"
        echo ""
        exit 1
    fi
}

# Function to validate environment variable values
validate_env_vars() {
    # Check for placeholder values
    local placeholder_vars=()
    
    [[ "$OFFICE365_TENANT_ID" == *"tenant_id_here"* ]] && placeholder_vars+=("OFFICE365_TENANT_ID")
    [[ "$OFFICE365_CLIENT_ID" == *"client_id_here"* ]] && placeholder_vars+=("OFFICE365_CLIENT_ID")
    [[ "$OFFICE365_CLIENT_SECRET" == *"client_secret_here"* ]] && placeholder_vars+=("OFFICE365_CLIENT_SECRET")
    [[ "$OFFICE365_SENDER_EMAIL" == *"yourdomain.com"* ]] && placeholder_vars+=("OFFICE365_SENDER_EMAIL")
    [[ "$GMAIL_RECIPIENT_EMAIL" == *"gmail_email_here"* ]] && placeholder_vars+=("GMAIL_RECIPIENT_EMAIL")
    
    if [ ${#placeholder_vars[@]} -ne 0 ]; then
        echo "❌ ERROR: Found placeholder values in environment variables:"
        printf '   - %s\n' "${placeholder_vars[@]}"
        echo ""
        echo "Please update your Portainer stack with actual credential values."
        echo ""
        exit 1
    fi
}

# Function to display configuration
show_config() {
    echo "✅ Configuration loaded successfully:"
    echo "   Office 365 Tenant: ${OFFICE365_TENANT_ID:0:8}..."
    echo "   Office 365 Client: ${OFFICE365_CLIENT_ID:0:8}..."
    echo "   Sender Email: $OFFICE365_SENDER_EMAIL"
    echo "   Recipient Email: $GMAIL_RECIPIENT_EMAIL"
    echo "   Zabbix Server: $ZABBIX_SERVER"
    echo "   Test Interval: ${TEST_INTERVAL:-60} seconds"
    echo "   Timeout: ${TIMEOUT_SECONDS:-300} seconds"
    echo "   Skip Gmail Setup: ${SKIP_GMAIL_SETUP:-false}"
    echo ""
}

# Main startup sequence
main() {
    # Ensure directories exist and are writable
    mkdir -p /app/credentials /app/logs || true
    # Try to take ownership of mounted volumes if running with sufficient privileges
    if command -v chown >/dev/null 2>&1; then
        chown -R $(id -u):$(id -g) /app/credentials /app/logs 2>/dev/null || true
    fi
    # Set restrictive permissions for credentials dir
    chmod 700 /app/credentials 2>/dev/null || true
    chmod 755 /app/logs 2>/dev/null || true
    # Ensure secure file creation defaults
    umask 077

    echo "🔍 Loading optional .env files..."
    for f in /app/.env /app/credentials/.env /.env; do
        if [ -f "$f" ]; then
            echo "   - sourcing $f"
            set -a
            # shellcheck disable=SC1090
            . "$f"
            set +a
        fi
    done

    echo "🔍 Checking environment variables..."
    check_env_vars
    
    echo "🔍 Validating environment variable values..."
    validate_env_vars
    
    echo "📋 Current configuration:"
    show_config
    echo "🔎 Debug (masked):"
    echo "   OFFICE365_TENANT_ID=${OFFICE365_TENANT_ID:0:8}..."
    echo "   OFFICE365_CLIENT_ID=${OFFICE365_CLIENT_ID:0:8}..."
    echo "   OFFICE365_CLIENT_SECRET=****"
    echo "   GMAIL_RECIPIENT_EMAIL=${GMAIL_RECIPIENT_EMAIL}"
    
    echo "🚀 Starting Email Delivery Monitor..."
    echo "   (Press Ctrl+C to stop)"
    echo ""

    # If credentials path is not writable and token doesn't exist, avoid hard fail by skipping Gmail setup
    if [ ! -w /app/credentials ] && [ ! -f /app/credentials/gmail_token.json ]; then
        echo "⚠️  /app/credentials is not writable and no token exists. Temporarily setting SKIP_GMAIL_SETUP=true to avoid crash."
        export SKIP_GMAIL_SETUP=true
    fi
    
    # Start the Python application
    exec python email_delivery_monitor.py
}

# Run main function
main "$@"