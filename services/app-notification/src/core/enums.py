from enum import StrEnum


class MessageTopics(StrEnum):
    EMAIL = "message.send.email"


class MessageTypes(StrEnum):
    TEST_MESSAGE = "TEST_MESSAGE"


class MessageSubjects(StrEnum):
    TEST_MESSAGE = "Тестовое письмо"


class MessageStatus(StrEnum):
    READY_TO_SEND = "READY_TO_SEND"
    SENT = "SENT"
    ERROR = "ERROR"
