# emailFunctions.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import sys
import modules.configFunctions as configFunctions

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def send_email(configFile, subject, body, to_email):
    # Retrieve the email configuration from the config file
    config = configFunctions.getConfig(configFile)

    email_config = config.get('email', {})  # Use config directly, no need for getConfig again

    # Extract email configuration values
    smtp_server = email_config.get('smtp_server', '')
    smtp_port = email_config.get('smtp_port', 587)
    smtp_username = email_config.get('smtp_username', '')
    smtp_password = email_config.get('smtp_password', '')

    # Check if any required values are missing
    if not smtp_server or not smtp_username or not smtp_password:
        raise ValueError("Email configuration is incomplete. Please check your config file.")

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = to_email
    msg['Subject'] = subject

    # Attach the body of the email
    msg.attach(MIMEText(body, 'plain'))

    # Connect to the SMTP server and send the email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, to_email, msg.as_string())
    logging.info(f"Sent email to {to_email}")


def send_subscription_reminder(configFile, email, days_left):
    subject = f"Subscription Reminder - {days_left} Days Left"
    body = f"Hello,\n\nYour subscription is set to end in {days_left} days. Please contact Trog on Discord (https://discord.gg/jp68q5C3pr) or reply to this email if you would like to continue with the subscription.\n\nThanks,\nTrog"

    send_email(configFile, subject, body, email)

def send_subscription_removed(configFile, email):
    subject = "Subscription Removed from Plex"
    body = "Hello,\n\nYour subscription has been removed from Plex. Please contact Trog on Discord (https://discord.gg/jp68q5C3pr) or reply to this email if you would like to continue with the subscription.\n\nThanks,\nTrog"

    send_email(configFile, subject, body, email)
