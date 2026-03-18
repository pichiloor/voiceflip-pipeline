from enum import Enum


class RequestStatus(str, Enum):
    # Possible states of a request
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
