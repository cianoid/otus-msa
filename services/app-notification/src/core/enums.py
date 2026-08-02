from enum import StrEnum


class MessageTopics(StrEnum):
    EMAIL = "message.send.email"


class MessageTypes(StrEnum):
    TEST_MESSAGE = "test_message"


class MessageStatus(StrEnum):
    READY_TO_SEND = "ready_to_send"
    SENT = "sent"
    ERROR = "error"
