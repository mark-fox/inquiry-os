import enum


class ExecutionMode(str, enum.Enum):
    REAL = "real"
    DUMMY = "dummy"