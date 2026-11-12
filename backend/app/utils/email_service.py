import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

def send_password_reset_email(to_email: str, reset_token: str) -> bool:
    """
    Attempts to send a password recovery email if SMTP is configured.
    Returns True if the email was successfully sent, False otherwise.
    Does NOT throw unhandled exceptions.
    """
    if not (settings.SMTP_SERVER and settings.SMTP_USERNAME and settings.SMTP_PASSWORD):
        return False

    try:
        reset_link = f"{settings.FRONTEND_URL}/#reset-password?token={reset_token}"
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Password Reset Instructions - {settings.PROJECT_NAME}"
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to_email

        plain_text = f"""Hello,

We received a request to reset your password for {settings.PROJECT_NAME}.
Please use the following token or link to set a new password:

Reset Token: {reset_token}
Reset Link: {reset_link}

This token is time-limited and will expire in 1 hour.
If you did not make this request, you can safely ignore this email.

Best regards,
The MindTrace Team
"""

        html_text = f"""<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1C2541; background-color: #F8FAFC; padding: 24px;">
  <div style="max-width: 520px; margin: 0 auto; background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 12px; padding: 32px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
      <h2 style="color: #0B132B; margin: 0; font-size: 22px;">MindTrace</h2>
    </div>
    <p style="font-size: 15px; line-height: 1.6; color: #334155;">Hello,</p>
    <p style="font-size: 14px; line-height: 1.6; color: #334155;">
      A password reset request was initiated for your MindTrace account. Click the button below to set a new secure password:
    </p>
    <div style="text-align: center; margin: 28px 0;">
      <a href="{reset_link}" style="background-color: #0B132B; color: #FFFFFF; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: 700; font-size: 14px; display: inline-block;">
        Reset Your Password
      </a>
    </div>
    <p style="font-size: 13px; color: #64748B; line-height: 1.5;">
      Alternatively, enter this reset token directly on the recovery page:<br/>
      <code style="background: #F1F5F9; padding: 4px 8px; border-radius: 4px; font-size: 13px; font-family: monospace; color: #4F46E5;">{reset_token}</code>
    </p>
    <hr style="border: none; border-top: 1px solid #E2E8F0; margin: 24px 0;" />
    <p style="font-size: 12px; color: #94A3B8; margin: 0;">
      This link and token are valid for 1 hour. If you did not request this, please disregard this email.
    </p>
  </div>
</body>
</html>"""

        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_text, "html"))

        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10)
        if settings.SMTP_TLS:
            server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"[Email Service] Failed to send email to {to_email}: {e}")
        return False

