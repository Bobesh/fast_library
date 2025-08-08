import logging
from typing import List, Optional
from datetime import date
from dataclasses import asdict
from pydantic import BaseModel, computed_field, Field
from fastapi import APIRouter, HTTPException, status, Depends, Header
from app.services.library_manager import LibraryManager
from app.core.dependencies import library_manager_dependency
from app.core.logging import log_debug

logger = logging.getLogger(__name__)
router = APIRouter()


class CopyInfoResponse(BaseModel):
    id: int
    book_id: int
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
    book_title: str

    @computed_field
    def borrower_full_name(self) -> str:
        return f"{self.borrower_first_name} {self.borrower_last_name}"

    @computed_field
    def days_until_due(self) -> int:
        from datetime import date

        return (self.due_date - date.today()).days


class BookWithCopiesResponse(BaseModel):
    id: int
    title: str
    isbn: Optional[str] = None
    year_published: Optional[int] = None
    available_copies: List[CopyInfoResponse]
    borrowed_copies: List[BorrowedCopyInfoResponse]

    @computed_field
    def total_copies(self) -> int:
        return len(self.available_copies) + len(self.borrowed_copies)

    @computed_field
    def available_copies_count(self) -> int:
        return len(self.available_copies)

    @computed_field
    def borrowed_copies_count(self) -> int:
        return len(self.borrowed_copies)

    @computed_field
    def is_available(self) -> bool:
        return len(self.available_copies) > 0

    @computed_field
    def availability_status(self) -> str:
        available = len(self.available_copies)
        total = len(self.available_copies) + len(self.borrowed_copies)

        if available == 0:
            return "Not available"
        elif available == total:
            return "Fully available"
        else:
            return f"{available} of {total} available"


class CreateBookRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Book title")
    isbn: Optional[str] = Field(None, max_length=13, description="ISBN number")
    year_published: Optional[int] = Field(
        None, ge=1000, le=2030, description="Publication year"
    )
    copies_count: int = Field(
        ..., ge=1, le=50, description="Number of copies to create (1-50)"
    )


class BookCreatedResponse(BaseModel):
    message: str
    book: BookWithCopiesResponse


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


# API Endpoints
@router.get("/", response_model=List[BookWithCopiesResponse])
async def get_books(
    library_manager: LibraryManager = Depends(library_manager_dependency),
):
    """Get all books"""
    log_debug(logger, "GET /books endpoint called")
    books = await library_manager.get_all_books()

    return [BookWithCopiesResponse.model_validate(asdict(book)) for book in books]


@router.get("/{book_id}", response_model=BookWithCopiesResponse)
async def get_book(
    book_id: int, library_manager: LibraryManager = Depends(library_manager_dependency)
):
    """Get book by ID"""
    log_debug(logger, f"GET /books/{book_id} endpoint called")
    book = await library_manager.get_book_details(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ID {book_id} not found",
        )

    return BookWithCopiesResponse.model_validate(asdict(book))


@router.post("/copies/{copy_id}/borrow", response_model=BorrowResponse)
async def borrow_copy(
    copy_id: int,
    x_user_id: int = Header(
        ..., alias="x-user-Id", description="ID of user borrowing the book"
    ),
    library_manager: LibraryManager = Depends(library_manager_dependency),
):
    """Borrow a specific copy of a book"""
    log_debug(
        logger,
        f"POST /books/copies/{copy_id}/borrow endpoint called for user {x_user_id}",
    )
    try:
        result = await library_manager.borrow_copy(copy_id, x_user_id)
        return BorrowResponse(
            message="Copy borrowed successfully",
            borrowing_details=BorrowingResultResponse.model_validate(asdict(result)),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/copies/{copy_id}/return", response_model=ReturnResponse)
async def return_book(
    copy_id: int, library_manager: LibraryManager = Depends(library_manager_dependency)
):
    """Return a book copy"""
    log_debug(logger, f"POST /books/copies/{copy_id}/return endpoint called")
    try:
        result = await library_manager.return_book(copy_id)
        return ReturnResponse(
            message="Book returned successfully",
            return_details=ReturnResultResponse.model_validate(asdict(result)),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/", response_model=BookCreatedResponse, status_code=status.HTTP_201_CREATED
)
async def create_book(
    book_data: CreateBookRequest,
    library_manager: LibraryManager = Depends(library_manager_dependency),
):
    """Create a new book with specified number of copies"""
    log_debug(logger, f"POST /books endpoint called for title: {book_data.title}")
    try:
        book_dict = book_data.model_dump(exclude_none=True)
        created_book = await library_manager.create_book(book_dict)

        return BookCreatedResponse(
            message=f"Book '{created_book.title}' created successfully with {created_book.total_copies} copies",
            book=BookWithCopiesResponse.model_validate(asdict(created_book)),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
