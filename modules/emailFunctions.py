import logging, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import modules.configFunctions as configFunctions

# Configure logging
logger = logging.getLogger("EmailFunctions")

# Helper Functions
def get_email_config(config):
    """
    Retrieve the email configuration from the global configuration.

    Args:
        config (dict): The global configuration dictionary.

    Returns:
        dict: The email configuration dictionary.
    """
    return config.get('email', {})


def get_message_template(config, key, default_template):
    """
    Retrieve a message template from the email configuration.

    Args:
        config (dict): The global configuration dictionary.
        key (str): The template key in the email configuration.
        default_template (str): The default template to use if the key is missing.

    Returns:
        str: The retrieved or default message template.
    """
    email_config = get_email_config(config)
    return email_config.get(key, default_template)


def create_email_message(subject, body, from_email, to_emails):
    """
    Create an email message object.

    Args:
        subject (str): Subject of the email.
        body (str): Body of the email.
        from_email (str): Sender's email address.
        to_emails (list): List of recipient email addresses.

    Returns:
        MIMEMultipart: The email message object.
    """
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = ', '.join(to_emails)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    return msg


# Main Functions
def send_email(config_file, subject, body, to_emails):
    """
    Send an email to the specified recipients.

    Args:
        config_file (str): Path to the configuration file.
        subject (str): Subject of the email.
        body (str): Body of the email.
        to_emails (list or str): Recipient email address(es).

    Returns:
        None
    """
    if not to_emails:
        logger.error("No recipient specified.")
        return

    if not isinstance(to_emails, (list, tuple, set)):
        to_emails = [to_emails]

    # Retrieve the email configuration
    config = configFunctions.getConfig(config_file)
    email_config = get_email_config(config)

    smtp_server = email_config.get('smtpServer', '')
    smtp_port = email_config.get('smtpPort', 587)
    smtp_username = email_config.get('smtpUsername', '')
    smtp_password = email_config.get('smtpPassword', '')
    smtp_send_as = email_config.get('smtpSendAs', smtp_username)

    # Validate required configuration fields
    if not smtp_server or not smtp_username or not smtp_password:
        logger.error("Email configuration is incomplete. Please check your config file.")
        return

    # Create the email message
    msg = create_email_message(subject, body, smtp_send_as, to_emails)

    # Send the email via SMTP
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.sendmail(smtp_send_as, to_emails, msg.as_string())
            logger.info(f"Email sent successfully to {', '.join(to_emails)} with subject: {subject}")
    except smtplib.SMTPException as e:
        logger.error(f"Failed to send email to {', '.join(to_emails)}. Error: {e}")


def send_subscription_reminder(config_file, to_email, primary_email, days_left, fourk, stream_count, one_m, three_m, six_m, twelve_m, dry_run):
    """
    Send a subscription reminder email.

    Args:
        config_file (str): Path to the configuration file.
        to_email (str or list): Recipient email address(es).
        primary_email (str): Primary email of the user.
        days_left (int): Days left until subscription ends.
        fourk (str): Whether the subscription includes 4K.
        stream_count (int): Number of allowed streams.
        one_m (float): Price for a 1-month subscription.
        three_m (float): Price for a 3-month subscription.
        six_m (float): Price for a 6-month subscription.
        twelve_m (float): Price for a 12-month subscription.
        dry_run (bool): If True, log the action instead of sending the email.

    Returns:
        None
    """
    config = configFunctions.getConfig(config_file)
    subject = get_message_template(config, 'reminderSubject', 'Subscription Reminder - {daysLeft} Days Left').format(daysLeft=days_left)
    body = get_message_template(config, 'reminderBody', (
        "Dear User,\n\nYour subscription for email: {primaryEmail} is set to expire in {daysLeft} days. "
        "Please contact us if you wish to continue your subscription by replying to this email.\n\nBest regards"
    )).format(primaryEmail=primary_email, daysLeft=days_left, streamCount=stream_count, fourk=fourk, oneM=one_m, threeM=three_m, sixM=six_m, twelveM=twelve_m)

    if dry_run:
        logger.info(f"Dry run: Subscription reminder email to {primary_email} skipped.")
    else:
        send_email(config_file, subject, body, to_email)


def send_subscription_removed(config_file, to_email, primary_email, dry_run):
    """
    Send a subscription removal notification email.

    Args:
        config_file (str): Path to the configuration file.
        to_email (str or list): Recipient email address(es).
        primary_email (str): Primary email of the user.
        dry_run (bool): If True, log the action instead of sending the email.

    Returns:
        None
    """
    config = configFunctions.getConfig(config_file)
    subject = get_message_template(config, 'removalSubject', 'Subscription Removed')
    body = get_message_template(config, 'removalBody', (
        "Dear User,\n\nYour subscription for email: {primaryEmail} has ended for Plex. "
        "Please contact us if you wish to continue your subscription by replying to this email.\n\nBest regards"
    )).format(primaryEmail=primary_email)

    if dry_run:
        logger.info(f"Dry run: Subscription removal email to {primary_email} skipped.")
    else:
        send_email(config_file, subject, body, to_email)
