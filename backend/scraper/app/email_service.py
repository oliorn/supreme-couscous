import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmailService:
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 587))
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_username)
        
    def send_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        html_content: Optional[str] = None,
        company_info: Optional[dict] = None
    ) -> dict:
        """
        Send an email using SMTP
        Returns: dict with success status and message
        """
        if not all([self.smtp_username, self.smtp_password]):
            return {
                "success": False,
                "error": "SMTP credentials not configured. Please set SMTP_USERNAME and SMTP_PASSWORD in .env file."
            }
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            
            # Use company name as sender name if provided
            if company_info and company_info.get('name'):
                sender_name = company_info.get('name')
            else:
                sender_name = "Email System"
            
            msg['From'] = f"{sender_name} <{self.from_email}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Attach plain text
            text_part = MIMEText(content, 'plain')
            msg.attach(text_part)
            
            # Attach HTML if provided, otherwise create simple HTML
            if html_content:
                html_part = MIMEText(html_content, 'html')
                msg.attach(html_part)
            else:
                # Simple HTML version
                html_simple = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
                    <div style="white-space: pre-line; padding: 20px; background-color: white; border-radius: 8px;">
                        {content}
                    </div>
                </body>
                </html>
                """
                html_part = MIMEText(html_simple, 'html')
                msg.attach(html_part)
            
            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()  # Secure the connection
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            return {
                "success": True,
                "message": f"Email sent successfully to {to_email}",
                "recipient": to_email,
                "subject": subject
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send email: {str(e)}",
                "recipient": to_email
            }


# Factory function to get email service
def get_email_service():
    return EmailService()