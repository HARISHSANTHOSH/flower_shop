
import os
import logging

import requests

from django.conf import settings


logger = logging.getLogger(__name__)


class WhatsAppAPIError(Exception):
    """
    Raised when Meta WhatsApp Cloud API returns an error.
    """

    def __init__(
        self,
        message,
        status_code=None,
        error_code=None,
        response_data=None,
    ):
        super().__init__(message)

        self.status_code = status_code
        self.error_code = error_code
        self.response_data = response_data or {}

        # Only transient failures should be retried by Celery.
        self.retryable = (
            status_code in (408, 429, 500, 502, 503, 504)
            or error_code in (80007, 130429, 131056)
        )


class WhatsAppService:
    """
    WhatsApp Cloud API service for Bloom Haven.
    """

    def __init__(self):

        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")

        self.phone_number_id = os.getenv(
            "WHATSAPP_PHONE_NUMBER_ID"
        )

        self.api_version = os.getenv(
            "WHATSAPP_API_VERSION", "v25.0"
        )

        self.admin_number = os.getenv(
            "WHATSAPP_ADMIN_NUMBER"
        )

        self.template_name = os.getenv(
            "WHATSAPP_TEMPLATE_NAME"
        )

        self.template_language = os.getenv(
            "WHATSAPP_TEMPLATE_LANGUAGE", "en_US"
        )

        if not all([
            self.access_token,
            self.phone_number_id,
            self.admin_number,
            self.template_name,
        ]):
            raise ValueError(
                "WhatsApp configuration is incomplete. "
                "Check your environment variables."
            )

        self.base_url = (
            f"https://graph.facebook.com/"
            f"{self.api_version}/"
            f"{self.phone_number_id}/messages"
        )

        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def send_template_message(
        self,
        to=None,
        template_name=None,
        language=None,
        components=None,
    ):
        """
        Send a WhatsApp template message.

        components:
            Optional list of WhatsApp template components.
            Used for dynamic order information.
        """

        recipient = to or self.admin_number

        template = {
            "name": template_name or self.template_name,
            "language": {
                "code": language or self.template_language
            },
        }

        if components:
            template["components"] = components

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "template",
            "template": template,
        }

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=(5, 20),
            )

        except requests.exceptions.Timeout as exc:
            logger.warning("WhatsApp API request timed out")
            raise

        except requests.exceptions.ConnectionError:
            logger.exception(
                "Could not connect to WhatsApp API"
            )
            raise

        except requests.exceptions.RequestException:
            logger.exception(
                "WhatsApp API network request failed"
            )
            raise

        try:
            response_data = response.json()
        except ValueError:
            response_data = {
                "message": response.text[:1000]
            }

        if not response.ok:

            error_data = response_data.get("error", {})

            error_code = error_data.get("code")

            error_message = error_data.get(
                "message", "Unknown WhatsApp API error"
            )

            logger.error(
                "WhatsApp API failed. HTTP status: %s, "
                "API error code: %s",
                response.status_code,
                error_code,
            )

            raise WhatsAppAPIError(
                message=error_message,
                status_code=response.status_code,
                error_code=error_code,
                response_data=response_data,
            )

        message_id = (
            response_data.get("messages", [{}])[0].get("id")
        )

        logger.info(
            "WhatsApp message accepted by Meta. "
            "Message ID: %s",
            message_id,
        )

        return response_data

    def send_admin_test_message(self):
        """
        Send Meta's standard hello_world template
        to the configured admin number.
        """

        return self.send_template_message(
            template_name="hello_world",
            language="en_US",
            to=self.admin_number,
        )
