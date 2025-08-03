import logging
from typing import List, Dict, Any, Optional
from app.core.logging import log_debug, log_info, log_error
from app.services.library_psql import LibraryPsql

logger = logging.getLogger(__name__)


class LibraryManager:
    """Business logic layer for library operations"""

    def __init__(self, data_access: LibraryPsql) -> None:
        self.data_access = data_access
        log_debug(logger, "LibraryManager initialized")

    async def get_all_books(self, include_copy_details: bool = False):
        """Get all books with availability information"""
        log_debug(logger, f"LibraryManager: Getting all books (include_copy_details={include_copy_details})")
        return await self.data_access.get_all_books_with_copies(include_copy_details)

    async def get_book_details(self, book_id: int, include_copy_details: bool = False):
        """Get detailed information about a specific book"""
        log_debug(logger,
                  f"LibraryManager: Getting book details for ID {book_id} (include_copy_details={include_copy_details})")
        return await self.data_access.get_book_by_id(book_id, include_copy_details)

    async def get_borrowed_books(self) -> List[Dict[str, Any]]:
        """Get all currently borrowed books"""
        log_debug(logger, "LibraryManager: Getting borrowed books")
        return await self.data_access.get_currently_borrowed_books()

    async def borrow_book(self, book_id: int, user_id: int) -> Dict[str, Any]:
        """
        Borrow a book for a user
        Business logic: check availability, validate user, etc.
        """
        log_info(logger, f"LibraryManager: User {user_id} attempting to borrow book {book_id}")

        # Could add business logic here like:
        # - Check if user has overdue books
        # - Check borrowing limits
        # - Validate user status

        try:
            result = await self.data_access.borrow_book(book_id, user_id)
            log_info(logger, f"LibraryManager: Successfully processed borrowing for user {user_id}")
            return result
        except ValueError as e:
            log_error(logger, f"LibraryManager: Borrowing failed - {e}")
            raise
        except Exception as e:
            log_error(logger, f"LibraryManager: Unexpected error during borrowing - {e}", exc_info=e)
            raise

    async def return_book(self, copy_id: int) -> Dict[str, Any]:
        """
        Return a book
        Business logic: calculate fines, update history, etc.
        """
        log_info(logger, f"LibraryManager: Attempting to return copy {copy_id}")

        try:
            result = await self.data_access.return_book(copy_id)
            log_info(logger, f"LibraryManager: Successfully processed return for copy {copy_id}")
            return result
        except ValueError as e:
            log_error(logger, f"LibraryManager: Return failed - {e}")
            raise
        except Exception as e:
            log_error(logger, f"LibraryManager: Unexpected error during return - {e}", exc_info=e)
            raise
