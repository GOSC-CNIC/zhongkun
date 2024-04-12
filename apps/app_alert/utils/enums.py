from enum import Enum


class AlertStatus(Enum):
    FIRING = "firing"
    RESOLVED = "resolved"
    WORK_ORDER = "work order"
