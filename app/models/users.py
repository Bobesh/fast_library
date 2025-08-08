from dataclasses import dataclass
from typing import Optional
from datetime import date


@dataclass(frozen=True)
class User:
    """User information"""
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    created_at: date

    @property
    def full_name(self) -> str:
        """Users full name"""
        return f"{self.first_name} {self.last_name}"
