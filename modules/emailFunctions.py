# emailFunctions.py
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import modules.configFunctions as configFunctions

def send_email(configFile, subject, body, to_emails):
    # Retrieve the email configuration from the config file
    config = configFunctions.getConfig(configFile)
    email_config = config.get('email', {})

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
    msg['To'] = ', '.join(to_emails)  # Combine multiple emails into a comma-separated string
    msg['Subject'] = subject

    # Attach the body of the email
    msg.attach(MIMEText(body, 'plain'))

    # Connect to the SMTP server and send the email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, to_emails, msg.as_string())

def send_subscription_reminder(configFile, toEmail, primaryEmail, days_left):
    subject = f"Subscription Reminder - {days_left} Days Left"
    body = f"Dear User,\n\nYour subscription for email: {primaryEmail} is set to expire in {days_left} days. Please contact us if you wish to continue your subscription please reply to this email or contact Trog on Discord (https://discord.gg/jp68q5C3pr).\n\nBest regards,\nThe TrogPlex Team"
    # send_email(configFile, subject, body, toEmail)
    logging.info(f"TEMP DISABLED EMAILS")

def send_subscription_removed(configFile, toEmail, primaryEmail):
    subject = "Subscription Removed"
    body = f"Dear User,\n\nYour subscription for email: {primaryEmail} has been removed from Trog's Plex. Please contact us if you wish to continue your subscription please reply to this email or contact Trog on Discord (https://discord.gg/jp68q5C3pr).\n\nBest regards,\nThe TrogPlex Team"
    # send_email(configFile, subject, body, toEmail)
    logging.info(f"TEMP DISABLED EMAILS")

