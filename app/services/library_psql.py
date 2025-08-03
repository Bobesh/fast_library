import logging
from typing import List, Optional, Union
from datetime import date, timedelta

import psycopg2

from app.core.database import DatabaseConnection
from app.core.logging import log_debug, log_error
from app.models.books import (
    BookWithCopies, BookSummary, BookDetails, BorrowedBook,
    BorrowingResult, ReturnResult, CopyInfo, BorrowedCopyInfo
)

logger = logging.getLogger(__name__)

# Table names as constants
BOOKS_TABLE_NAME = "books"
COPIES_TABLE_NAME = "copies"
USERS_TABLE_NAME = "users"
BORROWINGS_TABLE_NAME = "borrowings"


class LibraryPsql:
    """Data access layer for library operations"""

    @staticmethod
    def _get_book_base_query() -> str:
        """Base query for book information with copy counts"""
        return f"""
            SELECT b.id, b.title, b.isbn, b.year_published,
                   COUNT(c.id) as total_copies,
                   COUNT(CASE WHEN c.status = 'available' THEN 1 END) as available_copies,
                   COUNT(CASE WHEN c.status = 'borrowed' THEN 1 END) as borrowed_copies
            FROM {BOOKS_TABLE_NAME} b
            LEFT JOIN {COPIES_TABLE_NAME} c ON b.id = c.book_id
        """

    @staticmethod
    async def _get_available_copies_for_book(book_id: int, conn) -> List[CopyInfo]:
        """Get available copies for a specific book"""
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT id, status, created_at::date
                FROM {COPIES_TABLE_NAME}
                WHERE book_id = %s AND status = 'available'
                ORDER BY id
            """, (book_id,))
            rows = cursor.fetchall()

            return [CopyInfo(id=row[0], status=row[1], created_at=row[2]) for row in rows]

    @staticmethod
    async def _get_borrowed_copies_for_book(book_id: int, conn) -> List[BorrowedCopyInfo]:
        """Get borrowed copies for a specific book with borrower details"""
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT c.id as copy_id, u.id as borrower_id, u.first_name, u.last_name, u.email,
                       br.borrowed_at, br.due_date,
                       CASE WHEN br.due_date < CURRENT_DATE THEN true ELSE false END as is_overdue
                FROM {COPIES_TABLE_NAME} c
                JOIN {BORROWINGS_TABLE_NAME} br ON c.id = br.copy_id
                JOIN {USERS_TABLE_NAME} u ON br.user_id = u.id
                WHERE c.book_id = %s AND c.status = 'borrowed' AND br.returned_at IS NULL
                ORDER BY br.due_date
            """, (book_id,))
            rows = cursor.fetchall()

            return [
                BorrowedCopyInfo(
                    copy_id=row[0], borrower_id=row[1], borrower_first_name=row[2],
                    borrower_last_name=row[3], borrower_email=row[4], borrowed_at=row[5],
                    due_date=row[6], is_overdue=row[7]
                )
                for row in rows
            ]

    async def _create_book_with_copies(self, book_row: tuple, book_id: int, conn) -> BookWithCopies:
        """Create BookWithCopies object from database row"""
        available_copies = await self._get_available_copies_for_book(book_id, conn)
        borrowed_copies = await self._get_borrowed_copies_for_book(book_id, conn)

        return BookWithCopies(
            id=book_row[0], title=book_row[1], isbn=book_row[2], year_published=book_row[3],
            total_copies=book_row[4], available_copies_count=book_row[5],
            borrowed_copies_count=book_row[6], available_copies=available_copies,
            borrowed_copies=borrowed_copies
        )

    async def get_all_books_with_copies(self, include_copy_details: bool = False) -> Union[
        List[BookWithCopies], List[BookSummary]]:
        """Get all books with copy information"""
        try:
            log_debug(logger, f"Fetching all books (include_copy_details={include_copy_details})")

            with DatabaseConnection() as conn:
                with conn.cursor() as cursor:
                    query = self._get_book_base_query() + """
                        GROUP BY b.id, b.title, b.isbn, b.year_published
                        ORDER BY b.title
                    """
                    cursor.execute(query)
                    book_rows = cursor.fetchall()

                    if not include_copy_details:
                        books = [
                            BookSummary(
                                id=row[0], title=row[1], isbn=row[2], year_published=row[3],
                                total_copies=row[4], available_copies_count=row[5],
                                borrowed_copies_count=row[6]
                            )
                            for row in book_rows
                        ]
                        log_debug(logger, f"Retrieved {len(books)} books summary")
                        return books

                    # Full details
                    books = []
                    for book_row in book_rows:
                        book = await self._create_book_with_copies(book_row, book_row[0], conn)
                        books.append(book)

                    log_debug(logger, f"Retrieved {len(books)} books with full details")
                    return books

        except Exception as e:
            log_error(logger, f"Failed to fetch books: {e}", exc_info=e)
            raise

    async def get_book_by_id(self, book_id: int, include_copy_details: bool = False) -> Optional[
        Union[BookWithCopies, BookDetails]]:
        """Get book by ID with optional copy details"""
        try:
            log_debug(logger, f"Fetching book {book_id} (include_copy_details={include_copy_details})")

            with DatabaseConnection() as conn:
                with conn.cursor() as cursor:
                    query = self._get_book_base_query() + """
                        WHERE b.id = %s
                        GROUP BY b.id, b.title, b.isbn, b.year_published
                    """
                    cursor.execute(query, (book_id,))
                    row = cursor.fetchone()

                    if not row:
                        return None

                    if not include_copy_details:
                        book = BookDetails(
                            id=row[0], title=row[1], isbn=row[2], year_published=row[3],
                            total_copies=row[4], available_copies=row[5]
                        )
                        log_debug(logger, f"Found book: {book.title}")
                        return book

                    # Full details
                    book = await self._create_book_with_copies(row, book_id, conn)
                    log_debug(logger, f"Found book: {book.title}")
                    return book

        except Exception as e:
            log_error(logger, f"Failed to fetch book {book_id}: {e}", exc_info=e)
            raise

    async def get_currently_borrowed_books(self) -> List[BorrowedBook]:
        """Get all currently borrowed books"""
        try:
            log_debug(logger, "Fetching currently borrowed books")
            with DatabaseConnection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"""
                        SELECT b.id, b.title, u.first_name, u.last_name, u.email,
                               br.borrowed_at, br.due_date, c.id as copy_id,
                               CASE WHEN br.due_date < CURRENT_DATE THEN true ELSE false END as is_overdue
                        FROM {BORROWINGS_TABLE_NAME} br
                        JOIN {COPIES_TABLE_NAME} c ON br.copy_id = c.id
                        JOIN {BOOKS_TABLE_NAME} b ON c.book_id = b.id
                        JOIN {USERS_TABLE_NAME} u ON br.user_id = u.id
                        WHERE br.returned_at IS NULL
                        ORDER BY br.due_date
                    """)
                    rows = cursor.fetchall()

                    borrowings = [
                        BorrowedBook(
                            book_id=row[0], book_title=row[1], borrower_first_name=row[2],
                            borrower_last_name=row[3], borrower_email=row[4], borrowed_at=row[5],
                            due_date=row[6], copy_id=row[7], is_overdue=row[8]
                        )
                        for row in rows
                    ]

                    log_debug(logger, f"Retrieved {len(borrowings)} borrowed books")
                    return borrowings
        except Exception as e:
            log_error(logger, f"Failed to fetch borrowed books: {e}", exc_info=e)
            raise

    async def borrow_copy(self, copy_id: int, user_id: int) -> BorrowingResult:
        """Borrow a specific copy for a user"""
        try:
            log_debug(logger, f"Attempting to borrow copy {copy_id} for user {user_id}")
            with DatabaseConnection() as conn:
                # Transaction context manager - auto BEGIN/COMMIT/ROLLBACK
                with conn:
                    with conn.cursor() as cursor:
                        # Lock the copy row and check availability
                        cursor.execute(f"""
                            SELECT id, status, book_id FROM {COPIES_TABLE_NAME} 
                            WHERE id = %s FOR UPDATE
                        """, (copy_id,))
                        copy_row = cursor.fetchone()

                        if not copy_row:
                            raise ValueError(f"Copy {copy_id} not found")

                        if copy_row[1] != 'available':
                            raise ValueError(f"Copy {copy_id} is not available (current status: {copy_row[1]})")

                        book_id = copy_row[2]
                        due_date = date.today() + timedelta(days=30)

                        # Update copy status
                        cursor.execute(f"""
                            UPDATE {COPIES_TABLE_NAME} SET status = 'borrowed' WHERE id = %s
                        """, (copy_id,))

                        # Create borrowing record
                        cursor.execute(f"""
                            INSERT INTO {BORROWINGS_TABLE_NAME} (copy_id, user_id, due_date)
                            VALUES (%s, %s, %s)
                            RETURNING id, borrowed_at
                        """, (copy_id, user_id, due_date))
                        borrowing_row = cursor.fetchone()

                        # Context manager automatically commits here if no exception

                        result = BorrowingResult(
                            borrowing_id=borrowing_row[0],
                            copy_id=copy_id,
                            borrowed_at=borrowing_row[1],
                            due_date=due_date
                        )

                        log_debug(logger,
                                  f"Successfully borrowed copy {copy_id} (book {book_id}), borrowing ID: {result.borrowing_id}")
                        return result

        except Exception as e:
            # Context manager automatically rolled back on exception
            log_error(logger, f"Failed to borrow copy {copy_id}: {e}", exc_info=e)
            raise

    async def return_book(self, copy_id: int) -> ReturnResult:
        """Return a book"""
        try:
            log_debug(logger, f"Attempting to return copy {copy_id}")
            with DatabaseConnection() as conn:
                with conn:  # Transaction context manager
                    with conn.cursor() as cursor:
                        # Lock the borrowing record
                        cursor.execute(f"""
                            SELECT id FROM {BORROWINGS_TABLE_NAME} 
                            WHERE copy_id = %s AND returned_at IS NULL
                            FOR UPDATE
                        """, (copy_id,))
                        borrowing_row = cursor.fetchone()

                        if not borrowing_row:
                            raise ValueError(f"No active borrowing found for copy {copy_id}")

                        borrowing_id = borrowing_row[0]
                        return_date = date.today()

                        # Update borrowing record
                        cursor.execute(f"""
                            UPDATE {BORROWINGS_TABLE_NAME} 
                            SET returned_at = %s 
                            WHERE id = %s
                        """, (return_date, borrowing_id))

                        # Update copy status
                        cursor.execute(f"""
                            UPDATE {COPIES_TABLE_NAME} SET status = 'available' WHERE id = %s
                        """, (copy_id,))

                        # Auto-commit here

                        result = ReturnResult(
                            borrowing_id=borrowing_id,
                            copy_id=copy_id,
                            returned_at=return_date
                        )
                        log_debug(logger, f"Successfully returned copy {copy_id}")
                        return result

        except Exception as e:
            # Auto-rollback on exception
            log_error(logger, f"Failed to return copy {copy_id}: {e}", exc_info=e)
            raise
