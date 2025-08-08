import logging
from typing import Dict, Any
from fastapi import HTTPException, status
from app.core.logging import log_debug, log_info, log_error
from app.models.books import BorrowingResult, ReturnResult, BookWithCopies
from app.services.library_psql import LibraryPsql

logger = logging.getLogger(__name__)


class LibraryManager:
    """Business logic layer for library operations"""

    def __init__(self, data_access: LibraryPsql) -> None:
        self.data_access = data_access
        log_debug(logger, "LibraryManager initialized")

    async def get_all_books(self):
        """Get all books with availability information"""
        log_debug(logger, f"LibraryManager: Getting all books")
        try:
            return await self.data_access.get_all_books_with_copies()
        except Exception as e:
            log_error(
                logger, f"LibraryManager: Failed to get all books - {e}", exc_info=e
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve books",
            )

    async def get_book_details(self, book_id: int):
        """Get detailed information about a specific book"""
        log_debug(logger, f"LibraryManager: Getting book details for ID {book_id}")
        try:
            return await self.data_access.get_book_by_id(book_id)
        except Exception as e:
            log_error(
                logger,
                f"LibraryManager: Failed to get book details for ID {book_id} - {e}",
                exc_info=e,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve book details",
            )

    async def borrow_copy(self, book_id: int, user_id: int) -> BorrowingResult:
        """
        Borrow a book for a user
        """
        log_info(
            logger,
            f"LibraryManager: User {user_id} attempting to borrow book {book_id}",
        )

        try:
            result = await self.data_access.borrow_copy(book_id, user_id)
            log_info(
                logger,
                f"LibraryManager: Successfully processed borrowing for user {user_id}",
            )
            return result
        except ValueError as e:
            log_error(logger, f"LibraryManager: Borrowing failed - {e}")
            raise
        except Exception as e:
            log_error(
                logger,
                f"LibraryManager: Unexpected error during borrowing - {e}",
                exc_info=e,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process borrowing request",
            )

    async def return_book(self, copy_id: int) -> ReturnResult:
        """
        Return a book
        """
        log_info(logger, f"LibraryManager: Attempting to return copy {copy_id}")

        try:
            result = await self.data_access.return_book(copy_id)
            log_info(
                logger,
                f"LibraryManager: Successfully processed return for copy {copy_id}",
            )
            return result
        except ValueError as e:
            log_error(logger, f"LibraryManager: Return failed - {e}")
            raise
        except Exception as e:
            log_error(
                logger,
                f"LibraryManager: Unexpected error during return - {e}",
                exc_info=e,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process return request",
            )

    async def create_book(self, book_data: Dict[str, Any]) -> BookWithCopies:
        """
        Create a new book with copies
        """
        log_info(logger, f"LibraryManager: Creating book '{book_data.get('title')}'")

        try:
            book = await self.data_access.create_book(book_data)
            log_info(
                logger,
                f"LibraryManager: Successfully created book '{book.title}' with ID {book.id}",
            )
            return book
        except ValueError as e:
            log_error(logger, f"LibraryManager: Failed to create book - {e}")
            raise
        except Exception as e:
            log_error(
                logger,
                f"LibraryManager: Unexpected error creating book - {e}",
                exc_info=e,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create book",
            )
