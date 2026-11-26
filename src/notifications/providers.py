import logging

logger = logging.getLogger(__name__)


class BaseSMSProvider:
    name = 'Base'

    def send(self, *, phone_number: str, message: str) -> dict:
        raise NotImplementedError


class MockSMSProvider(BaseSMSProvider):
    """شبیه‌ساز ارسال پیامک برای محیط توسعه و تست"""
    name = 'MockSMS'

    def send(self, *, phone_number: str, message: str) -> dict:
        logger.info('[MOCK SMS] To: %s | Message: %s', phone_number, message)
        return {
            'success': True,
            'response': 'Simulated SMS logged in console.',
        }


def get_sms_provider() -> BaseSMSProvider:
    return MockSMSProvider()