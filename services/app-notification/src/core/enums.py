from enum import StrEnum


class MessageTopics(StrEnum):
    EMAIL = "message.send.email"


class MessageTypes(StrEnum):
    TEST_MESSAGE = "TEST_MESSAGE"


class MessageStatus(StrEnum):
    READY_TO_SEND = "READY_TO_SEND"
    SENT = "SENT"
    ERROR = "ERROR"
