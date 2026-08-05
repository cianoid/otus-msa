from enum import StrEnum


class MessageTopics(StrEnum):
    EMAIL = "message.send.email"


class MessageTypes(StrEnum):
    TEST_MESSAGE = "TEST_MESSAGE"
    ORDER_SUCCESS = "ORDER_SUCCESS"
    ORDER_FAILED = "ORDER_FAILED"


class MessageSubjects(StrEnum):
    TEST_MESSAGE = "Тестовое письмо"
    ORDER_SUCCESS = "Заказ успешно оформлен"
    ORDER_FAILED = "Не удалось оформить заказ"


class MessageStatus(StrEnum):
    READY_TO_SEND = "READY_TO_SEND"
    SENT = "SENT"
    ERROR = "ERROR"
