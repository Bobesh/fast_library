from dataclasses import dataclass
from typing import Optional, List
from datetime import date


@dataclass(frozen=True)
class CopyInfo:
    """Information about a specific copy"""
    id: int
    status: str
    created_at: date


@dataclass(frozen=True)
class BorrowedCopyInfo:
    """Information about a borrowed copy with borrowing details"""
    copy_id: int
    book_title: str
    borrower_id: int
    borrower_first_name: str
    borrower_last_name: str
    borrower_email: str
    borrowed_at: date
    due_date: date
    is_overdue: bool

    @property
    def borrower_full_name(self) -> str:
        return f"{self.borrower_first_name} {self.borrower_last_name}"

    @property
    def days_until_due(self) -> int:
        """Days until due (negative if overdue)"""
        return (self.due_date - date.today()).days


@dataclass(frozen=True)
class BaseBook:
    id: int
    title: str
    isbn: Optional[str]
    year_published: Optional[int]

@dataclass(frozen=True)
class BookWithCopies(BaseBook):
    """Book with detailed copy information"""
    available_copies: List[CopyInfo]
    borrowed_copies: List[BorrowedCopyInfo]

    @property
    def available_copies_count(self):
        return len(self.available_copies)

    @property
    def borrowed_copies_count(self):
        return len(self.borrowed_copies)

    @property
    def total_copies(self):
        return self.borrowed_copies_count + self.available_copies_count

    @property
    def is_available(self) -> bool:
        """Check if any copy is available for borrowing"""
        return self.available_copies_count > 0

    @property
    def availability_status(self) -> str:
        """Human readable availability status"""
        if self.available_copies_count == 0:
            return "Not available"
        elif self.available_copies_count == self.total_copies:
            return "Fully available"
        else:
            return f"{self.available_copies_count} of {self.total_copies} available"

    @property
    def overdue_copies(self) -> List[BorrowedCopyInfo]:
        """Get only overdue borrowed copies"""
        return [copy for copy in self.borrowed_copies if copy.is_overdue]


@dataclass(frozen=True)
class BookSummary:
    """Simplified book information without detailed copy lists"""
    id: int
    title: str
    isbn: Optional[str]
    year_published: Optional[int]
    total_copies: int
    available_copies_count: int
    borrowed_copies_count: int

    @property
    def is_available(self) -> bool:
        return self.available_copies_count > 0


@dataclass(frozen=True)
class BookDetails:
    """Detailed book information"""
    id: int
    title: str
    isbn: Optional[str]
    year_published: Optional[int]
    total_copies: int
    available_copies: int


@dataclass(frozen=True)
class BorrowingResult:
    """Result of borrowing operation"""
    borrowing_id: int
    copy_id: int
    borrowed_at: date
    due_date: date


@dataclass(frozen=True)
class ReturnResult:
    """Result of return operation"""
    borrowing_id: int
    copy_id: int
    returned_at: date