import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict
from app.core.config import settings

logger = logging.getLogger("scuilone.email")
logger.setLevel(logging.INFO)

# In-memory storage of last sent OTP for instant local development/debugging/testing
last_sent_otps: Dict[str, str] = {}


class EmailService:
    @staticmethod
    def send_otp_email(to_email: str, user_name: str, otp_code: str, verification_type: str = "email") -> bool:
        """
        Sends a 6-digit OTP verification code.
        Logs to console and stores in cache for developer ease.
        Transmits via SMTP if configured in environment.
        """
        last_sent_otps[to_email] = otp_code
        
        subject_map = {
            "email": "Verify Your Email - SCuilONE CRM",
            "mfa": "Your Multi-Factor Authentication Code - SCuilONE CRM",
            "reset": "Password Reset Code - SCuilONE CRM"
        }
        subject = subject_map.get(verification_type, "Verification Code - SCuilONE CRM")
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="color: #2563eb; margin: 0;">SCuilONE</h2>
                <p style="color: #64748b; font-size: 14px;">Multi-Industry Multi-Tenant CRM</p>
            </div>
            <p>Hello <strong>{user_name}</strong>,</p>
            <p>Your 6-digit verification code is:</p>
            <div style="background-color: #f1f5f9; padding: 16px; border-radius: 6px; text-align: center; font-size: 28px; font-weight: bold; letter-spacing: 6px; color: #1e293b; margin: 20px 0;">
                {otp_code}
            </div>
            <p style="color: #64748b; font-size: 13px;">This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes. If you did not request this code, please ignore this email.</p>
            <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
            <p style="color: #94a3b8; font-size: 11px; text-align: center;">© 2026 SCuilONE CRM Platform. All rights reserved.</p>
        </div>
        """

        # Log OTP prominently in terminal for development
        print(f"\n=======================================================")
        print(f"📧 [EMAIL SERVICE] To: {to_email}")
        print(f"🔑 [OTP CODE]: {otp_code}  (Type: {verification_type})")
        print(f"⏳ Expires in {settings.OTP_EXPIRE_MINUTES} minutes")
        print(f"=======================================================\n")
        
        if settings.ENABLE_REAL_EMAIL and settings.SMTP_HOST and settings.SMTP_USER:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
                msg["To"] = to_email
                msg.attach(MIMEText(html_content, "html"))

                with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                    server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())
                return True
            except Exception as e:
                logger.error(f"Failed to send email via SMTP: {e}")
                return False
                
        return True


email_service = EmailService()
