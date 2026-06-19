from enum import Enum

class VisibilityStatus(Enum):
    HIDDEN = "hidden"
    VISIBLE_TO_ALL = "visible to all"

class InvitationType(Enum):
    INVITATION = 'invitation'
    REQUEST = 'request'

class Status(Enum):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    DECLINED = 'declined'