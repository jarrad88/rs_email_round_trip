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
        
        self.config = self._load_config(config_file)
        self._setup_logging()
        self.gmail_service = None
        self.access_token = None
        
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
    
    def _get_office365_token(self) -> Optional[str]:
        """Get Office 365 access token using MSAL."""
        try:
            config = self.config['office365']
            app = msal.ConfidentialClientApplication(
                config['client_id'],
                authority=f"https://login.microsoftonline.com/{config['tenant_id']}",
                client_credential=config['client_secret']
            )
            
            # Get token for Microsoft Graph
            result = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
            
            if "access_token" in result:
                return result['access_token']
            else:
                self.logger.error(f"Failed to acquire token: {result.get('error_description')}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting Office 365 token: {e}")
            return None
    
    def _setup_gmail_service(self):
        """Setup Gmail API service."""
        try:
            SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
            creds = None
            
            config = self.config['gmail']
            token_file = config.get('token_file', 'gmail_token.json')
            credentials_file = config.get('credentials_file', 'gmail_credentials.json')
            
            # Load existing token
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            
            # If no valid credentials, get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not os.path.exists(credentials_file):
                        self.logger.error(f"Gmail credentials file {credentials_file} not found!")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
                    # For headless/container environments, use console flow
                    try:
                        creds = flow.run_local_server(port=0)
                    except Exception as browser_error:
                        self.logger.info("Browser authentication failed, trying console flow...")
                        creds = flow.run_console()
                
                # Save credentials for future use
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
            
            self.gmail_service = build('gmail', 'v1', credentials=creds)
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting up Gmail service: {e}")
            return False
    
    def send_test_email(self, test_id: str) -> bool:
        """Send test email via Office 365."""
        try:
            if not self.access_token:
                self.access_token = self._get_office365_token()
                if not self.access_token:
                    return False
            
            config = self.config['office365']
            monitoring_config = self.config['monitoring']
            
            # Create email content
            subject = f"{monitoring_config['subject_prefix']} - {test_id}"
            body = f"""
            Email Delivery Test
            
            Test ID: {test_id}
            Sent Time: {datetime.utcnow().isoformat()}Z
            
            This is an automated email delivery test. Please do not reply.
            """
            
            # Prepare email message
            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "Text",
                        "content": body
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": self.config['gmail']['recipient_email']
                            }
                        }
                    ]
                }
            }
            
            # Send email via Microsoft Graph API
            headers = {
                'Authorization': f'Bearer {self.access_token}',
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
                return True
            else:
                self.logger.error(f"Failed to send email: {response.status_code} - {response.text}")
                # Token might be expired, clear it
                if response.status_code == 401:
                    self.access_token = None
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
                        # Get message details
                        msg = self.gmail_service.users().messages().get(
                            userId='me', id=message['id']
                        ).execute()
                        
                        # Extract received time from headers
                        headers = msg['payload'].get('headers', [])
                        received_time = None
                        
                        for header in headers:
                            if header['name'].lower() == 'received':
                                # Parse the first (most recent) Received header
                                received_header = header['value']
                                # Extract timestamp using regex
                                time_match = re.search(r';.*?(\d{1,2}\s+\w{3}\s+\d{4}\s+\d{2}:\d{2}:\d{2})', received_header)
                                if time_match:
                                    try:
                                        from dateutil import parser
                                        received_time = parser.parse(time_match.group(1))
                                        break
                                    except:
                                        continue
                        
                        if received_time:
                            # Calculate delivery time (time since test started)
                            delivery_time = time.time() - start_time
                            self.logger.info(f"Email {test_id} delivered in {delivery_time:.2f} seconds")
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
