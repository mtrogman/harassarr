# emailFunctions.py
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import modules.configFunctions as configFunctions


def getEmailConfig(config):
    return config.get('email', {})

def getReminderSubject(config):
    emailConfig = getEmailConfig(config)
    return emailConfig.get('reminderSubject', 'Subscription Reminder - {daysLeft} Days Left')

def getReminderBody(config):
    emailConfig = getEmailConfig(config)
    return emailConfig.get('reminderBody', 'Dear User,\n\nYour subscription for email: {primaryEmail} is set to expire in {daysLeft} days. Please contact us if you wish to continue your subscription by replying to this email.\n\nBest regards')

def getRemovalSubject(config):
    emailConfig = getEmailConfig(config)
    return emailConfig.get('removalSubject', 'Subscription Removed')

def getRemovalBody(config):
    emailConfig = getEmailConfig(config)
    return emailConfig.get('removalBody', 'Dear User,\n\nYour subscription for email: {primaryEmail} has ended for Plex. Please contact us if you wish to continue your subscription by replying to this email.\n\nBest regards')


def sendEmail(configFile, subject, body, toEmails):
    if not toEmails:
        logging.error("No recipient specified.")
        return
    if not isinstance(toEmails, (list, tuple, set)):
        toEmails = [toEmails]

    # Retrieve the email configuration from the config file
    config = configFunctions.getConfig(configFile)
    emailConfig = config.get('email', {})

    # Extract email configuration values
    smtpServer = emailConfig.get('smtpServer', '')
    smtpPort = emailConfig.get('smtpPort', 587)
    smtpUsername = emailConfig.get('smtpUsername', '')
    smtpPassword = emailConfig.get('smtpPassword', '')

    # Check if any required values are missing
    if not smtpServer or not smtpUsername or not smtpPassword:
        raise ValueError("Email configuration is incomplete. Please check your config file.")

    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = smtpUsername
    msg['To'] = ', '.join(toEmails)  # Combine multiple emails into a comma-separated string
    msg['Subject'] = subject

    # Attach the body of the email
    msg.attach(MIMEText(body, 'plain'))

    # Connect to the SMTP server and send the email
    with smtplib.SMTP(smtpServer, smtpPort) as server:
        server.starttls()
        server.login(smtpUsername, smtpPassword)
        server.sendmail(smtpUsername, toEmails, msg.as_string())


def sendSubscriptionReminder(configFile, toEmail, primaryEmail, daysLeft, fourk, streamCount, oneM, threeM, sixM, twelveM, dryrun):
    config = configFunctions.getConfig(configFile)
    subject = getReminderSubject(config).format(daysLeft=daysLeft)
    body = getReminderBody(config).format(primaryEmail=primaryEmail, daysLeft=daysLeft, streamCount=streamCount, fourk=fourk, oneM=oneM, threeM=threeM, sixM=sixM, twelveM=twelveM)
    if dryrun:
        logging.info(f"EMAIL NOTIFICATION ({primaryEmail} SKIPPED DUE TO DRYRUN")
    else:
        sendEmail(configFile, subject, body, toEmail)


def sendSubscriptionRemoved(configFile, toEmail, primaryEmail, dryrun):
    config = configFunctions.getConfig(configFile)
    subject = getRemovalSubject(config)
    body = getRemovalBody(config).format(primaryEmail=primaryEmail)
    if dryrun:
        logging.info(f"EMAIL NOTIFICATION ({primaryEmail} SKIPPED DUE TO DRYRUN")
    else:
        sendEmail(configFile, subject, body, toEmail)

