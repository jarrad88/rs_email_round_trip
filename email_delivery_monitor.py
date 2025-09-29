#!/usr/bin/env python3
"""
Email Delivery Time Monitor
Sends emails from Office 365 to Gmail and measures delivery time.
Integrates with Zabbix for monitoring and alerting.
"""

import json
import logging
import time
import uuid
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import schedule
import sys
import os
try:
    # Python 3.9+
    from zoneinfo import ZoneInfo  # type: ignore
except Exception:
    ZoneInfo = None  # Fallback handled at runtime

# Microsoft Graph API imports
import msal
import requests

# Gmail API imports
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Zabbix integration
from pyzabbix import ZabbixMetric, ZabbixSender


class EmailDeliveryMonitor:
    """Monitor email delivery time between Office 365 and Gmail."""
    
    def __init__(self, config_file: str = None):
        """Initialize the email delivery monitor."""
        # Auto-detect config file if not specified
        if config_file is None:
            if os.path.exists("config.docker.json"):
                config_file = "config.docker.json"
            else:
                config_file = "config.json"

        # Load optional .env files before reading config so substitution works
        self._load_env_files([
            ".env",
            "/app/.env",
            "/app/credentials/.env",
        ])

        # Load config and initialize logging
        self.config = self._load_config(config_file)
        self._setup_logging()

        # Initialize runtime state
        self.gmail_service = None
        self.access_token = None
        self.token_expires_at = 0  # epoch seconds
        self.msal_app = None
        self.last_send_epoch = None  # record last send timestamp for accurate delivery calc
        self.last_message_id = None  # last generated Message-ID for logging/diagnostics
        # Timezone for displaying sent time (default to Sydney, DST-aware AEST/AEDT)
        tz_name = self.config.get('monitoring', {}).get('timezone', 'Australia/Sydney')
        try:
            if ZoneInfo is not None:
                self.local_tz = ZoneInfo(tz_name)
            else:
                from datetime import timezone
                self.local_tz = timezone(timedelta(hours=10), name='AEST')
        except Exception:
            from datetime import timezone
            self.local_tz = timezone(timedelta(hours=10), name='AEST')
        
    def _load_config(self, config_file: str) -> Dict[str, Any]:
        """Load configuration from JSON file with environment variable substitution."""
        try:
            with open(config_file, 'r') as f:
                config_content = f.read()
            
            # Substitute environment variables
            config_content = self._substitute_env_vars(config_content)
            
            return json.loads(config_content)
        except FileNotFoundError:
            print(f"Configuration file {config_file} not found!")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in configuration file: {e}")
            sys.exit(1)

    def _load_env_files(self, paths):
        """Load simple .env key=value files into environment (without external deps)."""
        def _parse_and_set(path: str):
            try:
                if not os.path.exists(path):
                    return False
                with open(path, 'r') as f:
                    for raw in f:
                        line = raw.strip()
                        if not line or line.startswith('#'):
                            continue
                        if '=' not in line:
                            continue
                        key, value = line.split('=', 1)
                        key = key.strip()
                        # Remove optional surrounding quotes
                        value = value.strip().strip('"').strip("'")
                        if key:
                            os.environ[key] = value
                return True
            except Exception:
                return False

        for p in paths:
            _parse_and_set(p)
    
    def _substitute_env_vars(self, content: str) -> str:
        """Substitute environment variables in configuration content."""
        import re
        
        def replace_env_var(match):
            var_expr = match.group(1)
            if ':' in var_expr:
                var_name, default_value = var_expr.split(':', 1)
                return os.getenv(var_name, default_value)
            else:
                var_name = var_expr
                env_value = os.getenv(var_name)
                if env_value is None:
                    raise ValueError(f"Environment variable {var_name} is required but not set")
                return env_value
        
        # Replace ${VAR_NAME} and ${VAR_NAME:default_value} patterns
        pattern = r'\$\{([^}]+)\}'
        return re.sub(pattern, replace_env_var, content)
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_config = self.config.get('logging', {})
        
        # Create logs directory if it doesn't exist
        log_file = log_config.get('file', 'email_delivery_monitor.log')
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # Setup rotating file handler
        from logging.handlers import RotatingFileHandler
        
        handler = RotatingFileHandler(
            log_file,
            maxBytes=log_config.get('max_file_size_mb', 10) * 1024 * 1024,
            backupCount=log_config.get('backup_count', 5)
        )
        
        # Setup logging format
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        
        # Configure logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, log_config.get('level', 'INFO')))
        self.logger.addHandler(handler)
        
        # Also log to console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
    
    def _get_office365_token(self, force: bool = False) -> Optional[str]:
        """Get or refresh an Office 365 access token using MSAL with simple caching.

        - If a token exists and is not expiring within 5 minutes, reuse it.
        - Otherwise, acquire a new token.
        - When force=True, always fetch a new token.
        """
        try:
            # Return cached token if still valid and not forcing refresh
            if not force and self.access_token and time.time() < (self.token_expires_at - 300):
                return self.access_token

            # Initialize MSAL app once for lightweight in-memory caching
            if not self.msal_app:
                config = self.config['office365']
                self.msal_app = msal.ConfidentialClientApplication(
                    config['client_id'],
                    authority=f"https://login.microsoftonline.com/{config['tenant_id']}",
                    client_credential=config['client_secret']
                )

            result = self.msal_app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
            if "access_token" in result:
                self.access_token = result['access_token']
                # expires_in is seconds until expiry
                expires_in = int(result.get('expires_in', 3600))
                self.token_expires_at = int(time.time()) + expires_in
                return self.access_token
            else:
                # Log a concise error; MSAL returns error and error_description
                err = result.get('error')
                desc = result.get('error_description')
                self.logger.error(f"Failed to acquire token: {err} - {desc}")
                return None
        except Exception as e:
            self.logger.error(f"Error getting Office 365 token: {e}")
            return None
    
    def _setup_gmail_service(self):
        """Setup Gmail API service."""
        try:
            # Allow skipping Gmail setup (e.g., first run or read-only volumes)
            skip = os.getenv('SKIP_GMAIL_SETUP', 'false').lower() == 'true'
            SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
            creds = None
            
            config = self.config['gmail']
            token_file = config.get('token_file', 'gmail_token.json')
            credentials_file = config.get('credentials_file', 'gmail_credentials.json')

            if skip:
                self.logger.warning("SKIP_GMAIL_SETUP=true; skipping Gmail API initialization.")
                self.gmail_service = None
                return True
            
            # Load existing token
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                    except Exception as refresh_err:
                        self.logger.error(f"Gmail token refresh failed: {refresh_err}")
                        # Fall through to re-auth flow below
                        creds = None
                else:
                    if not os.path.exists(credentials_file):
                        self.logger.error(f"Gmail credentials file {credentials_file} not found!")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                    # For headless/container environments, use console flow
                    try:
                        # Request offline access so we get a long-lived refresh token
                        creds = flow.run_local_server(port=0)
                    except Exception as browser_error:
                        self.logger.info("Browser authentication failed, trying console flow...")
                        # Build an auth URL explicitly requesting offline access and consent
                        auth_url, _ = flow.authorization_url(
                            access_type='offline',
                            prompt='consent',
                            include_granted_scopes='true'
                        )
                        self.logger.info(f"Open this URL to authorize Gmail access (offline): {auth_url}")
                        creds = flow.run_console()
                
                # Save credentials for future use
                try:
                    with open(token_file, 'w') as token:
                        token.write(creds.to_json())
                except PermissionError:
                    if skip:
                        self.logger.warning("Permissions error writing token, but SKIP_GMAIL_SETUP=true; continuing without Gmail.")
                        self.gmail_service = None
                        return True
                    raise
                
                # Validate we have a refresh token for long-lived access
                if not getattr(creds, 'refresh_token', None):
                    self.logger.warning(
                        "Gmail credentials do not include a refresh_token. The access token will expire. "
                        "Re-run auth with explicit consent (access_type=offline, prompt=consent)."
                    )
            
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            return True
            
        except PermissionError as e:
            # Respect skip flag on permission issues
            if os.getenv('SKIP_GMAIL_SETUP', 'false').lower() == 'true':
                self.logger.warning(f"Gmail setup skipped due to permission error: {e}")
                self.gmail_service = None
                return True
            self.logger.error(f"Error setting up Gmail service: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error setting up Gmail service: {e}")
            return False
    
    def send_test_email(self, test_id: str) -> bool:
        """Send test email via Office 365."""
        try:
            # Ensure we have a valid (non-expiring) token
            token = self._get_office365_token()
            if not token:
                return False
            
            config = self.config['office365']
            monitoring_config = self.config['monitoring']
            
            # Create email content
            subject = f"{monitoring_config['subject_prefix']} - {test_id}"
            local_sent = datetime.now(self.local_tz)
            # Format: DD/MM/YYYY hh:mm:ss AM/PM TZ (+offset)
            sent_str = local_sent.strftime('%d/%m/%Y %I:%M:%S %p %Z (%z)')
            body = f"""
            Email Delivery Test
            
            Test ID: {test_id}
            Sent Time: {sent_str}
            
            This is an automated email delivery test. Please do not reply.
            """
            
            # Prepare email message
            send_epoch = int(time.time())
            # Generate a unique RFC 5322 Message-ID using sender domain
            sender_email = self.config['office365']['sender_email']
            domain = sender_email.split('@')[-1] if '@' in sender_email else 'email-monitor.local'
            message_id = f"<{test_id}.{send_epoch}.{uuid.uuid4().hex[:8]}@{domain}>"
            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "Text",
                        "content": body
                    },
                    # Add deterministic headers so an Exchange transport rule can target this traffic
                    "internetMessageHeaders": [
                        {"name": "X-EmailMonitor", "value": "true"},
                        {"name": "X-EmailTestId", "value": test_id},
                        {"name": "X-EmailSendEpoch", "value": str(send_epoch)},
                        {"name": "Message-ID", "value": message_id},
                        {"name": "X-Monitor-Message-Id", "value": message_id},
                        {"name": "X-EmailMonitor-Sender", "value": config['sender_email']}
                    ],
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": self.config['gmail']['recipient_email']
                            }
                        }
                    ]
                },
                "saveToSentItems": False
            }
            
            # Send email via Microsoft Graph API
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"https://graph.microsoft.com/v1.0/users/{config['sender_email']}/sendMail",
                headers=headers,
                json=message,
                timeout=30
            )
            
            if response.status_code == 202:
                self.logger.info(f"Test email sent successfully with ID: {test_id}")
                # Record send epoch for accurate delivery timing
                self.last_send_epoch = send_epoch
                self.last_message_id = message_id
                return True
            
            # If token expired (401), refresh and retry once
            if response.status_code == 401:
                self.logger.warning("Graph returned 401; refreshing token and retrying once...")
                token = self._get_office365_token(force=True)
                if not token:
                    return False
                headers['Authorization'] = f'Bearer {token}'
                response = requests.post(
                    f"https://graph.microsoft.com/v1.0/users/{config['sender_email']}/sendMail",
                    headers=headers,
                    json=message,
                    timeout=30
                )
                if response.status_code == 202:
                    self.logger.info(f"Test email sent successfully after token refresh (ID: {test_id})")
                    self.last_send_epoch = send_epoch
                    self.last_message_id = message_id
                    return True
            
            # Non-202 or failed retry
            self.logger.error(f"Failed to send email: {response.status_code} - {response.text}")
            return False
                
        except Exception as e:
            self.logger.error(f"Error sending test email: {e}")
            return False
    
    def check_for_email(self, test_id: str, max_wait_time: int = 300) -> Optional[float]:
        """Check Gmail for the test email and return delivery time in seconds."""
        try:
            if not self.gmail_service:
                if not self._setup_gmail_service():
                    return None
                # If still no Gmail service (skipped), bail out gracefully
                if not self.gmail_service:
                    self.logger.info("Gmail service not initialized (skipped); cannot check for email this run.")
                    return None
            
            start_time = time.time()
            monitoring_config = self.config['monitoring']
            subject_pattern = f"{monitoring_config['subject_prefix']} - {test_id}"
            
            while time.time() - start_time < max_wait_time:
                try:
                    # Search for emails with the test ID
                    query = f'subject:"{subject_pattern}" newer_than:1h'
                    results = self.gmail_service.users().messages().list(
                        userId='me', q=query, maxResults=10
                    ).execute()
                    
                    messages = results.get('messages', [])
                    
                    for message in messages:
                        # Verify headers to avoid false positives
                        msg = self.gmail_service.users().messages().get(
                            userId='me', id=message['id'], format='metadata',
                            metadataHeaders=[
                                'X-EmailTestId', 'X-EmailMonitor', 'X-EmailSendEpoch',
                                'Message-ID', 'X-Monitor-Message-Id',
                                'Subject', 'To', 'Delivered-To'
                            ]
                        ).execute()

                        headers = {h['name'].lower(): h['value'] for h in msg.get('payload', {}).get('headers', [])}
                        if headers.get('x-emailmonitor', '').lower() != 'true':
                            continue
                        if headers.get('x-emailtestid') != test_id:
                            continue

                        # Compute delivery time using Gmail internalDate (ms since epoch)
                        internal_date = int(msg.get('internalDate', 0)) / 1000.0
                        delivery_time = None
                        # Prefer send epoch from header for cross-process correctness
                        header_send_epoch = None
                        x_send = headers.get('x-emailsendepoch')
                        if x_send:
                            try:
                                header_send_epoch = float(x_send)
                            except Exception:
                                header_send_epoch = None
                        base_send = header_send_epoch or self.last_send_epoch
                        if base_send:
                            delivery_time = max(0.0, internal_date - float(base_send))
                        else:
                            # Fallback to detection-based timing
                            delivery_time = time.time() - start_time

                        # Log message-id for diagnostics
                        gid = headers.get('message-id') or headers.get('x-monitor-message-id')
                        if gid and self.last_message_id:
                            suffix = " (msg-id verified)" if gid == self.last_message_id else " (msg-id mismatch)"
                        else:
                            suffix = ""
                        self.logger.info(
                            f"Email {test_id} delivered in {delivery_time:.2f} seconds (gmail id {message['id']}){suffix}"
                        )
                        return delivery_time
                
                except HttpError as e:
                    self.logger.error(f"Gmail API error: {e}")
                    time.sleep(5)
                    continue
                
                # Wait before next check
                time.sleep(5)
            
            self.logger.warning(f"Email {test_id} not received within {max_wait_time} seconds")
            return None
            
        except Exception as e:
            self.logger.error(f"Error checking for email: {e}")
            return None
    
    def send_to_zabbix(self, delivery_time: Optional[float], test_id: str):
        """Send delivery time metric to Zabbix."""
        try:
            zabbix_config = self.config.get('zabbix', {})
            if not zabbix_config.get('enabled', False):
                return
            
            # Prepare metrics
            metrics = []
            
            if delivery_time is not None:
                # Successful delivery
                metrics.append(ZabbixMetric(
                    zabbix_config['host'],
                    'email.delivery.time',
                    delivery_time
                ))
                metrics.append(ZabbixMetric(
                    zabbix_config['host'],
                    'email.delivery.success',
                    1
                ))
            else:
                # Failed delivery
                metrics.append(ZabbixMetric(
                    zabbix_config['host'],
                    'email.delivery.success',
                    0
                ))
                metrics.append(ZabbixMetric(
                    zabbix_config['host'],
                    'email.delivery.time',
                    -1  # Indicate failure
                ))
            
            # Send to Zabbix
            zbx = ZabbixSender(
                zabbix_config['server'],
                int(zabbix_config.get('port', 10051))
            )
            result = zbx.send(metrics)
            
            if result.failed == 0:
                self.logger.info(f"Successfully sent {len(metrics)} metrics to Zabbix")
            else:
                self.logger.warning(f"Failed to send {result.failed} out of {result.total} metrics to Zabbix")
                
        except Exception as e:
            self.logger.error(f"Error sending metrics to Zabbix: {e}")
    
    def run_test(self):
        """Run a single email delivery test."""
        test_id = str(uuid.uuid4())[:8]
        self.logger.info(f"Starting email delivery test {test_id}")
        
        # Record start time
        start_time = time.time()
        
        # Send test email
        if not self.send_test_email(test_id):
            self.logger.error(f"Failed to send test email {test_id}")
            self.send_to_zabbix(None, test_id)
            return
        
        # Wait for email delivery
        timeout = self.config['monitoring'].get('timeout_seconds', 300)
        # Ensure timeout is an integer (environment variables are strings)
        timeout = int(timeout)
        delivery_time = self.check_for_email(test_id, timeout)
        
        # Send results to Zabbix
        self.send_to_zabbix(delivery_time, test_id)
        
        if delivery_time:
            self.logger.info(f"Test {test_id} completed successfully in {delivery_time:.2f} seconds")
        else:
            self.logger.error(f"Test {test_id} failed - email not received within timeout")
    
    def start_monitoring(self):
        """Start continuous monitoring with scheduled tests."""
        self.logger.info("Starting email delivery monitoring...")
        
        # Setup Gmail service at startup
        if not self._setup_gmail_service():
            self.logger.error("Failed to setup Gmail service. Exiting.")
            return
        
        # Schedule tests
        interval = self.config['monitoring'].get('test_interval_seconds', 60)
        # Ensure interval is an integer (environment variables are strings)
        interval = int(interval)
        schedule.every(interval).seconds.do(self.run_test)
        
        # Run initial test
        self.run_test()
        
        # Start scheduler
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Monitoring stopped by user.")
        except Exception as e:
            self.logger.error(f"Monitoring error: {e}")


def main():
    """Main entry point."""
    # Use Docker config if running in container, otherwise use regular config
    config_file = "config.docker.json" if os.path.exists("/app") else "config.json"
    monitor = EmailDeliveryMonitor(config_file)
    
    # Check if running as one-time test or continuous monitoring
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        print("Running single test...")
        monitor.run_test()
    else:
        print("Starting continuous monitoring (Ctrl+C to stop)...")
        monitor.start_monitoring()


if __name__ == "__main__":
    main()
