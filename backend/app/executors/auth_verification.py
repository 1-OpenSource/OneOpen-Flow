"""Email, OTP, TOTP, and human-in-the-loop verification executors."""

from __future__ import annotations

import email
import imaplib
import re
import time
from email.header import decode_header
from email.message import Message
from typing import Any
from urllib.parse import urlparse

from app.executors.base import NodeExecutor, registry

OTP_PATTERNS = [
    re.compile(r"\b(\d{6})\b"),
    re.compile(r"\b(\d{4})\b"),
    re.compile(r"(?:code|otp|passcode|verification)[^\d]{0,20}(\d{4,8})", re.I),
    re.compile(r"(?:is|:)\s*(\d{4,8})\b", re.I),
]

LINK_PATTERNS = [
    re.compile(r"https?://[^\s<>\"]+", re.I),
]


class AuthVerificationExecutor(NodeExecutor):
    node_types = {
        "wait_for_email",
        "extract_email_otp",
        "extract_email_verification_link",
        "open_verification_link",
        "generate_totp",
        "verify_totp",
        "human_otp_input",
        "fill_otp",
    }

    def execute(self, *, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        node_type = context.get("node_type", "")
        if node_type == "wait_for_email":
            return self._wait_for_email(config, context)
        if node_type == "extract_email_otp":
            return self._extract_otp(config, context)
        if node_type == "extract_email_verification_link":
            return self._extract_link(config, context)
        if node_type == "open_verification_link":
            return self._open_verification_link(config, context)
        if node_type == "generate_totp":
            return self._generate_totp(config, context)
        if node_type == "verify_totp":
            return self._verify_totp(config, context)
        if node_type == "human_otp_input":
            return self._human_otp_input(config, context)
        if node_type == "fill_otp":
            return self._fill_otp(config, context)
        return {
            "status": "failed",
            "failure_classification": "workflow_configuration_error",
            "error": f"Unknown auth node type: {node_type}",
        }

    def _wait_for_email(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        secrets = context.get("secrets") or {}
        host = config.get("imapHost") or secrets.get(config.get("imapHostSecret", "IMAP_HOST"))
        username = config.get("username") or secrets.get(config.get("usernameSecret", "IMAP_USERNAME"))
        password = config.get("password") or secrets.get(config.get("passwordSecret", "IMAP_PASSWORD"))
        folder = config.get("folder", "INBOX")
        timeout_seconds = float(config.get("timeoutSeconds", 120))
        poll_interval = float(config.get("pollIntervalSeconds", 5))
        subject_contains = (config.get("subjectContains") or "").lower()
        from_contains = (config.get("fromContains") or "").lower()
        to_contains = (config.get("toContains") or "").lower()
        unread_only = bool(config.get("unreadOnly", True))
        mark_seen = bool(config.get("markSeen", True))

        if not host or not username or not password:
            return {
                "status": "failed",
                "failure_classification": "workflow_configuration_error",
                "error": "IMAP host, username, and password are required (use secrets)",
            }

        deadline = time.time() + timeout_seconds
        last_error = None
        while time.time() < deadline:
            try:
                message = _fetch_matching_email(
                    host=str(host),
                    username=str(username),
                    password=str(password),
                    folder=str(folder),
                    subject_contains=subject_contains,
                    from_contains=from_contains,
                    to_contains=to_contains,
                    unread_only=unread_only,
                    mark_seen=mark_seen,
                    use_ssl=bool(config.get("useSsl", True)),
                    port=int(config.get("port") or (993 if config.get("useSsl", True) else 143)),
                )
                if message:
                    body = message["body"]
                    return {
                        "status": "passed",
                        "outputs": {
                            "subject": message["subject"],
                            "from": message["from"],
                            "to": message["to"],
                            "body": body,
                            "html": message.get("html") or "",
                            "messageId": message.get("messageId"),
                            "receivedAt": message.get("date"),
                        },
                        "logs": [f"Matched email: {message['subject']}"],
                    }
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
            time.sleep(poll_interval)

        return {
            "status": "failed",
            "failure_classification": "authentication_failure",
            "error": last_error or f"No matching email within {timeout_seconds}s",
        }

    def _extract_otp(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        previous = context.get("previous_result") or {}
        body = str(
            config.get("text")
            or previous.get("outputs", {}).get("body")
            or previous.get("outputs", {}).get("html")
            or ""
        )
        pattern = config.get("pattern")
        otp = None
        if pattern:
            match = re.search(str(pattern), body, re.I)
            otp = match.group(1) if match and match.groups() else (match.group(0) if match else None)
        else:
            for compiled in OTP_PATTERNS:
                match = compiled.search(body)
                if match:
                    otp = match.group(1)
                    break
        if not otp:
            return {
                "status": "failed",
                "failure_classification": "authentication_failure",
                "error": "Could not extract OTP from email body",
            }
        output_key = config.get("outputKey", "otp")
        return {
            "status": "passed",
            "outputs": {output_key: otp, "otp": otp},
            "logs": ["Extracted OTP (masked in UI as needed)"],
        }

    def _extract_link(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        previous = context.get("previous_result") or {}
        body = str(
            config.get("text")
            or previous.get("outputs", {}).get("html")
            or previous.get("outputs", {}).get("body")
            or ""
        )
        url_contains = (config.get("urlContains") or "").lower()
        link_text_contains = (config.get("linkTextContains") or "").lower()
        pattern = config.get("pattern")

        candidates: list[str] = []
        if pattern:
            for match in re.finditer(str(pattern), body, re.I):
                candidates.append(match.group(1) if match.groups() else match.group(0))
        else:
            # Prefer href="..."
            for match in re.finditer(r'href=["\'](https?://[^"\']+)["\']', body, re.I):
                candidates.append(match.group(1))
            for compiled in LINK_PATTERNS:
                candidates.extend(compiled.findall(body))

        filtered = []
        for url in candidates:
            cleaned = url.rstrip(").,]>\"'")
            if url_contains and url_contains not in cleaned.lower():
                continue
            if link_text_contains and link_text_contains not in body.lower():
                # soft filter — keep if url itself matches keywords
                if link_text_contains not in cleaned.lower():
                    continue
            filtered.append(cleaned)

        if not filtered:
            return {
                "status": "failed",
                "failure_classification": "authentication_failure",
                "error": "No verification link found in email",
            }

        # Prefer verify/confirm/activate style links
        preferred = next(
            (
                u
                for u in filtered
                if any(k in u.lower() for k in ("verify", "confirm", "activate", "validation", "token"))
            ),
            filtered[0],
        )
        output_key = config.get("outputKey", "verificationUrl")
        return {
            "status": "passed",
            "outputs": {output_key: preferred, "verificationUrl": preferred, "allLinks": filtered[:10]},
            "logs": [f"Extracted verification link host={urlparse(preferred).netloc}"],
        }

    def _open_verification_link(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Resolves URL then delegates to local browser open_url."""
        previous = context.get("previous_result") or {}
        url = (
            config.get("url")
            or previous.get("outputs", {}).get("verificationUrl")
            or previous.get("outputs", {}).get("url")
        )
        if not url:
            return {
                "status": "failed",
                "failure_classification": "workflow_configuration_error",
                "error": "verification URL is required",
            }
        from app.executors.local_browser import execute_local_browser
        from app.storage.service import StorageService

        run_id = context.get("run_id")
        node_id = context.get("node_id") or "open-verification-link"
        return execute_local_browser(
            config={"url": url, **{k: v for k, v in config.items() if k != "url"}},
            node_type="open_url",
            secrets=context.get("secrets") or {},
            storage=StorageService(),
            run_id=run_id,
            node_id=str(node_id),
        )

    def _generate_totp(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        try:
            import pyotp
        except ImportError:
            return {
                "status": "failed",
                "failure_classification": "infrastructure_error",
                "error": "pyotp is not installed",
            }
        secrets = context.get("secrets") or {}
        secret = config.get("secret") or secrets.get(config.get("secretKey", "TOTP_SECRET"))
        if not secret:
            return {
                "status": "failed",
                "failure_classification": "workflow_configuration_error",
                "error": "TOTP secret is required",
            }
        digits = int(config.get("digits", 6))
        interval = int(config.get("intervalSeconds", 30))
        totp = pyotp.TOTP(str(secret).replace(" ", ""), digits=digits, interval=interval)
        code = totp.now()
        output_key = config.get("outputKey", "otp")
        return {
            "status": "passed",
            "outputs": {output_key: code, "otp": code, "validForSeconds": interval},
            "logs": ["Generated TOTP code"],
        }

    def _verify_totp(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        try:
            import pyotp
        except ImportError:
            return {
                "status": "failed",
                "failure_classification": "infrastructure_error",
                "error": "pyotp is not installed",
            }
        secrets = context.get("secrets") or {}
        secret = config.get("secret") or secrets.get(config.get("secretKey", "TOTP_SECRET"))
        code = str(config.get("code") or config.get("otp") or "")
        if not secret or not code:
            return {
                "status": "failed",
                "failure_classification": "workflow_configuration_error",
                "error": "TOTP secret and code are required",
            }
        digits = int(config.get("digits", 6))
        interval = int(config.get("intervalSeconds", 30))
        window = int(config.get("validWindow", 1))
        totp = pyotp.TOTP(str(secret).replace(" ", ""), digits=digits, interval=interval)
        valid = totp.verify(code, valid_window=window)
        return {
            "status": "passed" if valid else "failed",
            "outputs": {"valid": valid},
            "failure_classification": None if valid else "authentication_failure",
            "error": None if valid else "TOTP code is invalid or expired",
        }

    def _human_otp_input(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Pause the workflow until an operator provides an OTP."""
        prompt = config.get("prompt") or "Enter the OTP / verification code to continue"
        timeout_seconds = int(config.get("timeoutSeconds", 600))
        return {
            "status": "approval_required",
            "pause": True,
            "outputs": {
                "prompt": prompt,
                "inputType": "otp",
                "masked": True,
                "timeoutSeconds": timeout_seconds,
                "hint": config.get("hint") or "Paste the code from SMS, authenticator, or email",
            },
            "logs": [f"Waiting for human OTP input: {prompt}"],
        }

    def _fill_otp(self, config: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Fill an OTP into a browser field using a previously extracted/generated value."""
        previous = context.get("previous_result") or {}
        otp = (
            config.get("value")
            or config.get("otp")
            or previous.get("outputs", {}).get("otp")
        )
        if not otp:
            return {
                "status": "failed",
                "failure_classification": "workflow_configuration_error",
                "error": "OTP value is required (from prior email/TOTP/human input node)",
            }
        from app.executors.local_browser import execute_local_browser
        from app.storage.service import StorageService

        fill_config = {
            **config,
            "value": str(otp),
            "label": config.get("label") or "OTP",
            "placeholder": config.get("placeholder") or "Enter code",
        }
        return execute_local_browser(
            config=fill_config,
            node_type="fill_input",
            secrets=context.get("secrets") or {},
            storage=StorageService(),
            run_id=context.get("run_id"),
            node_id=str(context.get("node_id") or "fill-otp"),
        )


def _decode_mime(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    chunks: list[str] = []
    for part, encoding in parts:
        if isinstance(part, bytes):
            chunks.append(part.decode(encoding or "utf-8", errors="replace"))
        else:
            chunks.append(part)
    return "".join(chunks)


def _message_bodies(msg: Message) -> tuple[str, str]:
    text_body = ""
    html_body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition") or "")
            if "attachment" in disposition:
                continue
            try:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                decoded = payload.decode(charset, errors="replace")
            except Exception:  # noqa: BLE001
                continue
            if content_type == "text/plain" and not text_body:
                text_body = decoded
            elif content_type == "text/html" and not html_body:
                html_body = decoded
    else:
        payload = msg.get_payload(decode=True) or b""
        charset = msg.get_content_charset() or "utf-8"
        decoded = payload.decode(charset, errors="replace")
        if msg.get_content_type() == "text/html":
            html_body = decoded
        else:
            text_body = decoded
    return text_body, html_body


def _fetch_matching_email(
    *,
    host: str,
    username: str,
    password: str,
    folder: str,
    subject_contains: str,
    from_contains: str,
    to_contains: str,
    unread_only: bool,
    mark_seen: bool,
    use_ssl: bool,
    port: int,
) -> dict[str, Any] | None:
    client: imaplib.IMAP4 | imaplib.IMAP4_SSL
    if use_ssl:
        client = imaplib.IMAP4_SSL(host, port)
    else:
        client = imaplib.IMAP4(host, port)
    try:
        client.login(username, password)
        client.select(folder)
        criteria = ["UNSEEN"] if unread_only else ["ALL"]
        status, data = client.search(None, *criteria)
        if status != "OK":
            return None
        ids = data[0].split()
        # Newest first
        for mail_id in reversed(ids[-50:]):
            status, msg_data = client.fetch(mail_id, "(RFC822)")
            if status != "OK" or not msg_data or not msg_data[0]:
                continue
            raw = msg_data[0][1]
            if not isinstance(raw, (bytes, bytearray)):
                continue
            msg = email.message_from_bytes(raw)
            subject = _decode_mime(msg.get("Subject"))
            from_addr = _decode_mime(msg.get("From"))
            to_addr = _decode_mime(msg.get("To"))
            if subject_contains and subject_contains not in subject.lower():
                continue
            if from_contains and from_contains not in from_addr.lower():
                continue
            if to_contains and to_contains not in to_addr.lower():
                continue
            text_body, html_body = _message_bodies(msg)
            if mark_seen:
                client.store(mail_id, "+FLAGS", "\\Seen")
            return {
                "subject": subject,
                "from": from_addr,
                "to": to_addr,
                "body": text_body or re.sub(r"<[^>]+>", " ", html_body),
                "html": html_body,
                "messageId": msg.get("Message-ID"),
                "date": msg.get("Date"),
            }
        return None
    finally:
        try:
            client.logout()
        except Exception:  # noqa: BLE001
            pass
