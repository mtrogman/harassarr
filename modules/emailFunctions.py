# modules/emailFunctions.py
import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from modules import configFunctions

def _get_email_cfg(configFile: str):
    cfg = configFunctions.getConfig(configFile)
    ecfg = cfg.get("email", {}) if isinstance(cfg, dict) else {}
    host = ecfg.get("smtpServer")
    port = ecfg.get("smtpPort")
    user = ecfg.get("smtpUsername")
    pwd  = ecfg.get("smtpPassword")
    send_as = ecfg.get("smtpSendAs") or user
    from_name = ecfg.get("fromName") or "Plex Admin"
    return {
        "host": host, "port": port, "user": user, "pwd": pwd,
        "send_as": send_as, "from_name": from_name,
        "reminderSubject": ecfg.get("reminderSubject"),
        "reminderBody": ecfg.get("reminderBody"),
        "removalSubject": ecfg.get("removalSubject"),
        "removalBody": ecfg.get("removalBody"),
    }

def _build_message(from_name: str, from_addr: str, to_addrs: list[str], subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = formataddr((from_name, from_addr))
    msg["To"] = ", ".join([a for a in to_addrs if a])
    msg["Subject"] = subject
    msg["Reply-To"] = from_addr
    msg.set_content(body)
    return msg

def _send_smtp(cfg: dict, msg: EmailMessage, dryrun: bool):
    host = cfg.get("host"); port = cfg.get("port")
    user = cfg.get("user"); pwd = cfg.get("pwd")

    if not host or not port or not user or not pwd:
        logging.error("Email SMTP not configured: smtpServer/smtpPort/smtpUsername/smtpPassword missing.")
        return

    if not msg["To"]:
        logging.info("Email skipped: no recipients.")
        return

    if dryrun:
        logging.info("[DRY-RUN] Would EMAIL %s (subject=%r)", msg["To"], msg["Subject"])
        return

    try:
        with smtplib.SMTP(host, int(port)) as s:
            s.ehlo()
            s.starttls()
            s.login(user, pwd)
            s.send_message(msg)
        logging.info("Email sent to %s", msg["To"])
    except Exception as e:
        logging.error("SMTP send failed to %s: %s", msg["To"], e)

def _fmt(v): return "" if v is None else str(v)

def _render(template: str, ctx: dict) -> str:
    try:
        return template.format_map(ctx)
    except Exception as e:
        logging.error("Email template render failed: %s", e)
        return template

def sendSubscriptionReminder(
    configFile: str,
    toEmails: list[str] | None,
    primaryEmail: str,
    daysLeft: int,
    fourk: str,
    streamCount: int,
    oneM: str, threeM: str, sixM: str, twelveM: str,
    dryrun: bool = False
):
    if not toEmails:
        logging.info("Email reminder skipped for %s: no recipients configured.", primaryEmail)
        return

    cfg = _get_email_cfg(configFile)
    subj_tpl = cfg.get("reminderSubject")
    body_tpl = cfg.get("reminderBody")
    if not subj_tpl or not body_tpl:
        logging.error("Email reminder templates missing in config: email.reminderSubject/body")
        return

    ctx = {
        "primaryEmail": primaryEmail,
        "daysLeft": daysLeft,
        "fourk": fourk,
        "streamCount": streamCount,
        "oneM": _fmt(oneM),
        "threeM": _fmt(threeM),
        "sixM": _fmt(sixM),
        "twelveM": _fmt(twelveM),
    }

    msg = _build_message(cfg["from_name"], cfg["send_as"], toEmails,
                         _render(subj_tpl, ctx), _render(body_tpl, ctx))
    _send_smtp(cfg, msg, dryrun)

def sendSubscriptionRemoved(
    configFile: str,
    toEmails: list[str] | None,
    primaryEmail: str,
    days_left: int,
    fourk: str,
    streamCount: int,
    oneM: str, threeM: str, sixM: str, twelveM: str,
    dryrun: bool = False
):
    if not toEmails:
        logging.info("Email removal notice skipped for %s: no recipients configured.", primaryEmail)
        return

    cfg = _get_email_cfg(configFile)
    subj_tpl = cfg.get("removalSubject")
    body_tpl = cfg.get("removalBody")
    if not subj_tpl or not body_tpl:
        logging.error("Email removal templates missing in config: email.removalSubject/body")
        return

    # Use {daysLeft} in templates for consistency
    ctx = {
        "primaryEmail": primaryEmail,
        "daysLeft": days_left,
        "fourk": fourk,
        "streamCount": streamCount,
        "oneM": _fmt(oneM),
        "threeM": _fmt(threeM),
        "sixM": _fmt(sixM),
        "twelveM": _fmt(twelveM),
    }

    msg = _build_message(cfg["from_name"], cfg["send_as"], toEmails,
                         _render(subj_tpl, ctx), _render(body_tpl, ctx))
    _send_smtp(cfg, msg, dryrun)
