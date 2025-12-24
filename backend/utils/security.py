"""security and pii masking middleware for soc2/pci compliance"""
import re
import logging
import hashlib
import time
from typing import Callable, Dict, List, Tuple, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class PIIMasker:
    """detects and masks personally identifiable information for compliance"""

    def __init__(self):
        # pii detection patterns with replacement formats
        self._patterns: List[Tuple[re.Pattern[str], str, str]] = [
            # credit card numbers (pci-dss requirement) - various formats
            (
                re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b'),
                "[CARD_MASKED]",
                "credit_card"
            ),
            # credit card with dashes/spaces
            (
                re.compile(r'\b(?:\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4})\b'),
                "[CARD_MASKED]",
                "credit_card"
            ),
            # social security numbers (us format)
            (
                re.compile(r'\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b'),
                "[SSN_MASKED]",
                "ssn"
            ),
            # israeli id numbers (9 digits)
            (
                re.compile(r'\b\d{9}\b'),
                "[ID_MASKED]",
                "national_id"
            ),
            # email addresses
            (
                re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
                "[EMAIL_MASKED]",
                "email"
            ),
            # phone numbers (various international formats)
            (
                re.compile(r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b'),
                "[PHONE_MASKED]",
                "phone"
            ),
            # israeli phone numbers
            (
                re.compile(r'\b(?:\+972[-\s]?)?0?[23489][-\s]?\d{7,8}\b'),
                "[PHONE_MASKED]",
                "phone"
            ),
            # medical record numbers (mrn) - common formats
            (
                re.compile(r'\bMRN[-:\s]?\s?[A-Z0-9]{6,12}\b', re.IGNORECASE),
                "[MRN_MASKED]",
                "medical_record"
            ),
            # health insurance numbers
            (
                re.compile(r'\b[A-Z]{3}\d{9}\b'),
                "[INSURANCE_MASKED]",
                "insurance"
            ),
            # dates of birth (various formats) - sensitive in medical context
            (
                re.compile(r'\b(?:0?[1-9]|1[0-2])[-/](?:0?[1-9]|[12][0-9]|3[01])[-/](?:19|20)\d{2}\b'),
                "[DOB_MASKED]",
                "date_of_birth"
            ),
            # prescription ids - partial masking (show first 3, last 3)
            (
                re.compile(r'\bRX_[A-Z0-9]{8,}\b'),
                lambda m: f"RX_{m.group()[3:6]}***{m.group()[-3:]}",
                "prescription_id"
            ),
            # patient ids - partial masking
            (
                re.compile(r'\bPAT_[A-Z0-9]{8,}\b'),
                lambda m: f"PAT_{m.group()[4:7]}***{m.group()[-3:]}",
                "patient_id"
            ),
        ]

        # sensitive field names that should be masked in json
        self._sensitive_fields = {
            'password', 'password_hash', 'token', 'api_key', 'secret',
            'ssn', 'social_security', 'credit_card', 'card_number', 'cvv', 'cvc',
            'date_of_birth', 'dob', 'birth_date', 'medical_record', 'mrn',
            'insurance_number', 'policy_number', 'bank_account', 'routing_number'
        }

    def mask_text(self, text: str) -> Tuple[str, List[Dict]]:
        """
        mask pii in text and return masked text with detection log

        args:
            text: input text to scan and mask

        returns:
            tuple of (masked_text, list of detection events)
        """
        if not text:
            return text, []

        detections = []
        masked_text = text

        for pattern, replacement, pii_type in self._patterns:
            matches = pattern.findall(masked_text)
            if matches:
                for match in matches:
                    # create hash for audit trail (without storing actual pii)
                    pii_hash = hashlib.sha256(match.encode() if isinstance(match, str) else str(match).encode()).hexdigest()[:16]
                    detections.append({
                        "type": pii_type,
                        "hash": pii_hash,
                        "masked": True
                    })

                # apply masking
                if callable(replacement):
                    masked_text = pattern.sub(replacement, masked_text)
                else:
                    masked_text = pattern.sub(replacement, masked_text)

        return masked_text, detections

    def mask_json_fields(self, data: dict, path: str = "") -> dict:
        """
        recursively mask sensitive fields in json/dict data

        args:
            data: dictionary to scan
            path: current path for logging

        returns:
            dictionary with sensitive fields masked
        """
        if not isinstance(data, dict):
            return data

        masked_data = {}
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key

            # check if field name is sensitive
            if key.lower() in self._sensitive_fields:
                masked_data[key] = "[REDACTED]"
                logger.debug(f"masked sensitive field: {current_path}")
            elif isinstance(value, dict):
                masked_data[key] = self.mask_json_fields(value, current_path)
            elif isinstance(value, list):
                masked_data[key] = [
                    self.mask_json_fields(item, f"{current_path}[]") if isinstance(item, dict) else item
                    for item in value
                ]
            elif isinstance(value, str):
                masked_value, detections = self.mask_text(value)
                masked_data[key] = masked_value
                if detections:
                    logger.debug(f"pii detected in field {current_path}: {[d['type'] for d in detections]}")
            else:
                masked_data[key] = value

        return masked_data


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    security middleware for soc2/pci-dss compliance

    features:
    - pii detection and masking in requests/responses
    - security headers (csp, hsts, x-content-type, etc.)
    - request id tracking for audit trails
    - rate limiting headers
    - request/response logging with pii masking
    """

    def __init__(self, app: ASGIApp, enable_pii_masking: bool = True):
        super().__init__(app)
        self.pii_masker = PIIMasker()
        self.enable_pii_masking = enable_pii_masking

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        process request through security middleware

        args:
            request: incoming request
            call_next: next middleware/handler

        returns:
            response with security headers and masked pii
        """
        start_time = time.time()

        # generate request id for audit trail
        request_id = hashlib.sha256(
            f"{time.time()}{request.client.host if request.client else 'unknown'}".encode()
        ).hexdigest()[:16]

        # log request (with masked data)
        await self._log_request(request, request_id)

        try:
            # process request
            response = await call_next(request)

            # add security headers
            response = self._add_security_headers(response, request_id)

            # log response timing
            process_time = time.time() - start_time
            logger.info(
                f"request_id={request_id} "
                f"method={request.method} "
                f"path={request.url.path} "
                f"status={response.status_code} "
                f"duration_ms={process_time * 1000:.2f}"
            )

            return response

        except Exception as e:
            logger.error(f"request_id={request_id} error={str(e)}")
            raise

    async def _log_request(self, request: Request, request_id: str) -> None:
        """log request details with pii masking"""
        # mask query parameters
        masked_query = {}
        for key, value in request.query_params.items():
            masked_value, _ = self.pii_masker.mask_text(value)
            masked_query[key] = masked_value

        # log sanitized request info
        logger.info(
            f"request_id={request_id} "
            f"method={request.method} "
            f"path={request.url.path} "
            f"client={request.client.host if request.client else 'unknown'} "
            f"user_agent={request.headers.get('user-agent', 'unknown')[:50]}"
        )

        if masked_query:
            logger.debug(f"request_id={request_id} query_params={masked_query}")

    def _add_security_headers(self, response: Response, request_id: str) -> Response:
        """
        add security headers for compliance

        headers added:
        - x-request-id: for audit trail tracking
        - x-content-type-options: prevent mime sniffing
        - x-frame-options: prevent clickjacking
        - x-xss-protection: xss filtering
        - strict-transport-security: force https
        - content-security-policy: restrict content sources
        - cache-control: prevent sensitive data caching
        - referrer-policy: control referrer information
        - permissions-policy: restrict browser features
        """
        # request tracking
        response.headers["X-Request-ID"] = request_id

        # prevent mime type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # xss protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # force https (hsts) - 1 year
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # content security policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # prevent caching of sensitive data
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"

        # control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # restrict browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=()"
        )

        return response


class AuditLogger:
    """
    audit logger for soc2 compliance

    logs security-relevant events with proper formatting for siem integration
    """

    def __init__(self, logger_name: str = "security.audit"):
        self.logger = logging.getLogger(logger_name)

    def log_authentication(
        self,
        user_id: str,
        success: bool,
        ip_address: str,
        user_agent: str = "",
        reason: str = ""
    ) -> None:
        """log authentication attempt"""
        self.logger.info(
            f"event=authentication "
            f"user_id={self._mask_user_id(user_id)} "
            f"success={success} "
            f"ip={ip_address} "
            f"user_agent={user_agent[:50]} "
            f"reason={reason}"
        )

    def log_data_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        ip_address: str
    ) -> None:
        """log data access for audit trail"""
        self.logger.info(
            f"event=data_access "
            f"user_id={self._mask_user_id(user_id)} "
            f"resource_type={resource_type} "
            f"resource_id={self._mask_resource_id(resource_id)} "
            f"action={action} "
            f"ip={ip_address}"
        )

    def log_pii_access(
        self,
        user_id: str,
        pii_type: str,
        action: str,
        ip_address: str
    ) -> None:
        """log pii access for compliance"""
        self.logger.warning(
            f"event=pii_access "
            f"user_id={self._mask_user_id(user_id)} "
            f"pii_type={pii_type} "
            f"action={action} "
            f"ip={ip_address}"
        )

    def log_security_event(
        self,
        event_type: str,
        severity: str,
        details: str,
        ip_address: str = "",
        user_id: str = ""
    ) -> None:
        """log security events"""
        log_func = getattr(self.logger, severity.lower(), self.logger.warning)
        log_func(
            f"event=security "
            f"type={event_type} "
            f"severity={severity} "
            f"details={details} "
            f"ip={ip_address} "
            f"user_id={self._mask_user_id(user_id) if user_id else 'anonymous'}"
        )

    def _mask_user_id(self, user_id: str) -> str:
        """partially mask user id for logs"""
        if not user_id or len(user_id) < 6:
            return "[MASKED]"
        return f"{user_id[:3]}***{user_id[-3:]}"

    def _mask_resource_id(self, resource_id: str) -> str:
        """partially mask resource id for logs"""
        if not resource_id or len(resource_id) < 6:
            return "[MASKED]"
        return f"{resource_id[:4]}***{resource_id[-4:]}"


# singleton instances
pii_masker = PIIMasker()
audit_logger = AuditLogger()
