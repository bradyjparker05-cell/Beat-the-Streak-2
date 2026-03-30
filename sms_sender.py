"""
SMS Sender via Email-to-SMS Gateway
Sends text messages using T-Mobile's email gateway
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


class SMSSender:
    def __init__(self, gmail_address: str, gmail_app_password: str, phone_number: str):
        """
        Initialize SMS sender
        
        Args:
            gmail_address: Your Gmail address (e.g., 'your.email@gmail.com')
            gmail_app_password: Gmail app password (NOT your regular password)
            phone_number: 10-digit phone number (e.g., '1234567890')
        """
        self.gmail_address = gmail_address
        self.gmail_app_password = gmail_app_password
        self.phone_number = phone_number
        
        # T-Mobile email-to-SMS gateway
        self.sms_gateway = f"{phone_number}@tmomail.net"
    
    def send_sms(self, message: str) -> bool:
        """
        Send SMS message via email gateway
        
        Args:
            message: Text message to send
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.gmail_address
            msg['To'] = self.sms_gateway
            msg['Subject'] = ''  # No subject for SMS
            
            # Add message body
            msg.attach(MIMEText(message, 'plain'))
            
            # Connect to Gmail SMTP server
            with smtplib.SMTP('smtp.gmail.com', 587) as server:
                server.starttls()  # Secure connection
                server.login(self.gmail_address, self.gmail_app_password)
                server.send_message(msg)
            
            print(f"SMS sent successfully to {self.phone_number}")
            return True
            
        except Exception as e:
            print(f"Error sending SMS: {e}")
            return False


def send_daily_picks(message: str):
    """
    Main function to send daily picks
    Reads credentials from environment variables
    """
    # Get credentials from environment variables
    gmail_address = os.environ.get('GMAIL_ADDRESS')
    gmail_password = os.environ.get('GMAIL_APP_PASSWORD')
    phone_number = os.environ.get('PHONE_NUMBER')
    
    if not all([gmail_address, gmail_password, phone_number]):
        raise ValueError("Missing required environment variables: GMAIL_ADDRESS, GMAIL_APP_PASSWORD, PHONE_NUMBER")
    
    # Send SMS
    sender = SMSSender(gmail_address, gmail_password, phone_number)
    return sender.send_sms(message)


if __name__ == "__main__":
    # Test message
    test_message = "This is a test message from your MLB Hit Predictor!"
    send_daily_picks(test_message)
