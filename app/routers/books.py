import logging
from typing import List, Optional, Union
from datetime import date
from dataclasses import asdict
from pydantic import BaseModel, computed_field
from fastapi import APIRouter, HTTPException, status, Depends
from app.services.library_manager import LibraryManager
from app.core.dependencies import library_manager_dependency
from app.core.logging import log_debug
from app.models.books import BookWithCopies

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic Response Models s computed fields
class CopyInfoResponse(BaseModel):
    id: int
    status: str
    created_at: date


class BorrowedCopyInfoResponse(BaseModel):
    copy_id: int
    borrower_id: int
    borrower_first_name: str
    borrower_last_name: str
    borrower_email: str
    borrowed_at: date
    due_date: date
    is_overdue: bool

    @computed_field
    @property
    def borrower_full_name(self) -> str:
        return f"{self.borrower_first_name} {self.borrower_last_name}"

    @computed_field
    @property
    def days_until_due(self) -> int:
        from datetime import date
        return (self.due_date - date.today()).days


class BookWithCopiesResponse(BaseModel):
    id: int
    title: str
    isbn: Optional[str] = None
    year_published: Optional[int] = None
    total_copies: int
    available_copies_count: int
    borrowed_copies_count: int
    available_copies: List[CopyInfoResponse]
    borrowed_copies: List[BorrowedCopyInfoResponse]

    @computed_field
    @property
    def is_available(self) -> bool:
        return self.available_copies_count > 0

    @computed_field
    @property
    def availability_status(self) -> str:
        if self.available_copies_count == 0:
            return "Not available"
        elif self.available_copies_count == self.total_copies:
            return "Fully available"
        else:
            return f"{self.available_copies_count} of {self.total_copies} available"


class BookSummaryResponse(BaseModel):
    id: int
    title: str
    isbn: Optional[str] = None
    year_published: Optional[int] = None
    total_copies: int
    available_copies_count: int
    borrowed_copies_count: int

    @computed_field
    @property
    def is_available(self) -> bool:
        return self.available_copies_count > 0


class BookDetailsResponse(BaseModel):
    id: int
    title: str
    isbn: Optional[str] = None
    year_published: Optional[int] = None
    total_copies: int
    available_copies: int


class BorrowedBookResponse(BaseModel):
    book_id: int
    book_title: str
    borrower_first_name: str
    borrower_last_name: str
    borrower_email: str
    borrowed_at: date
    due_date: date
    copy_id: int
    is_overdue: bool

    @computed_field
    @property
    def borrower_full_name(self) -> str:
        return f"{self.borrower_first_name} {self.borrower_last_name}"

    @computed_field
    @property
    def days_until_due(self) -> int:
        from datetime import date
        return (self.due_date - date.today()).days


class BorrowingResultResponse(BaseModel):
    borrowing_id: int
    copy_id: int
    borrowed_at: date
    due_date: date


class ReturnResultResponse(BaseModel):
    borrowing_id: int
    copy_id: int
    returned_at: date


class BorrowResponse(BaseModel):
    message: str
    borrowing_details: BorrowingResultResponse


class ReturnResponse(BaseModel):
    message: str
    return_details: ReturnResultResponse


def dataclass_to_pydantic(dataclass_obj, pydantic_model):
    """Convert dataclass to pydantic model"""
    return pydantic_model.model_validate(asdict(dataclass_obj))


def convert_dataclass_list(dataclass_list, pydantic_model):
    """Convert list of dataclasses to list of pydantic models"""
    return [dataclass_to_pydantic(item, pydantic_model) for item in dataclass_list]


# API Endpoints
@router.get("/", response_model=List[Union[BookWithCopiesResponse, BookSummaryResponse]])
async def get_books(
        include_details: bool = False,
        library_manager: LibraryManager = Depends(library_manager_dependency)
):
    """Get all books with optional detailed copy information"""
    log_debug(logger, f"GET /books endpoint called (include_details={include_details})")
    books = await library_manager.get_all_books(include_copy_details=include_details)

    if include_details:
        return convert_dataclass_list(books, BookWithCopiesResponse)
    else:
        return convert_dataclass_list(books, BookSummaryResponse)


@router.get("/borrowed", response_model=List[BorrowedBookResponse])
async def get_borrowed_books(library_manager: LibraryManager = Depends(library_manager_dependency)):
    """Get all currently borrowed books"""
    log_debug(logger, "GET /books/borrowed endpoint called")
    borrowed_books = await library_manager.get_borrowed_books()
    return convert_dataclass_list(borrowed_books, BorrowedBookResponse)


@router.get("/{book_id}", response_model=Union[BookWithCopiesResponse, BookDetailsResponse])
async def get_book(
        book_id: int,
        include_details: bool = False,
        library_manager: LibraryManager = Depends(library_manager_dependency)
):
    """Get book details by ID with optional copy details"""
    log_debug(logger, f"GET /books/{book_id} endpoint called (include_details={include_details})")
    book = await library_manager.get_book_details(book_id, include_copy_details=include_details)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ID {book_id} not found"
        )

    if include_details and isinstance(book, BookWithCopies):
        return dataclass_to_pydantic(book, BookWithCopiesResponse)
    else:
        return dataclass_to_pydantic(book, BookDetailsResponse)


@router.post("/copies/{copy_id}/borrow", response_model=BorrowResponse)
async def borrow_copy(
        copy_id: int,
        user_id: int,
        library_manager: LibraryManager = Depends(library_manager_dependency)
):
    """Borrow a specific copy of a book"""
    log_debug(logger, f"POST /books/copies/{copy_id}/borrow endpoint called for user {user_id}")
    try:
        result = await library_manager.borrow_copy(copy_id, user_id)
        return BorrowResponse(
            message="Copy borrowed successfully",
            borrowing_details=dataclass_to_pydantic(result, BorrowingResultResponse)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/copies/{copy_id}/return", response_model=ReturnResponse)
async def return_book(
        copy_id: int,
        library_manager: LibraryManager = Depends(library_manager_dependency)
):
    """Return a book copy"""
    log_debug(logger, f"POST /books/copies/{copy_id}/return endpoint called")
    try:
        result = await library_manager.return_book(copy_id)
        return ReturnResponse(
            message="Book returned successfully",
            return_details=dataclass_to_pydantic(result, ReturnResultResponse)
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )