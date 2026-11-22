
from dataclasses import dataclass


@dataclass
class User:
    id: int
    username: str
    role: str
    is_active: int
    created_at: str
