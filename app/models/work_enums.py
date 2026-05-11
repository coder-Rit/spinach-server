from __future__ import annotations

from enum import Enum


class ProjectStatus(str, Enum):
    OPEN = "OPEN"
    CLOSE = "CLOSE"


class WorkItemType(str, Enum):
    STORY = "STORY"
    TASK = "TASK"


class WorkItemStatus(str, Enum):
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    CODE_COMPLETE = "CODE_COMPLETE"
    DEPLOYED_ON_STAGE = "DEPLOYED_ON_STAGE"
    DONE = "DONE"

