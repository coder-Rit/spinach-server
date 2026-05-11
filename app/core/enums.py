from enum import Enum


class BaseStrEnum(str, Enum):
    @classmethod
    def has_value(cls, value):
        return value in cls._value2member_map_

    @classmethod
    def keys(cls):
        """Returns a list of all the enum keys."""
        return cls._member_names_

    @classmethod
    def values(cls):
        """Returns a list of all the enum values."""
        return list(cls._value2member_map_.keys())

    def __str__(self):
        return str(self.value)


class APIUserTypeEnum(BaseStrEnum):
    PORTAL = "PORTAL"
    WORKER = "WORKER"
