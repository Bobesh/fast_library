import logging
from typing import List, Optional, Dict, Any
from datetime import date, timedelta

import psycopg2

from app.core.database import DatabaseConnection
from app.core.logging import log_debug, log_error
from app.models.books import (
    BookWithCopies,
    BorrowingResult, ReturnResult, CopyInfo, BorrowedCopyInfo, BaseBook
)

logger = logging.getLogger(__name__)

BOOKS_TABLE_NAME = "books"
COPIES_TABLE_NAME = "copies"
USERS_TABLE_NAME = "users"
BORROWINGS_TABLE_NAME = "borrowings"


class LibraryPsql:
    """Data access layer for library operations"""

    @staticmethod
    def _get_books(cursor, book_id: Optional[int] = None) -> List[BaseBook]:
        """Get books with optional filtering by ID"""
        query = f"SELECT id, title, isbn, year_published FROM {BOOKS_TABLE_NAME}"
        params = ()

        if book_id is not None:
            query += " WHERE id = %s"
            params = (book_id,)

        query += " ORDER BY title"
        cursor.execute(query, params)

        return [
            BaseBook(
                id=row[0],
                title=row[1],
                isbn=row[2],
                year_published=row[3]
            )
            for row in cursor.fetchall()
        ]

    @staticmethod
    def _get_copies(cursor, book_id: Optional[int] = None) -> Dict[int, List[CopyInfo]]:
        """Get copies with optional filtering by book ID"""
        query = f"SELECT id, book_id, status, created_at FROM {COPIES_TABLE_NAME}"
        params = ()

        if book_id is not None:
            query += " WHERE book_id = %s"
            params = (book_id,)

        query += " ORDER BY book_id, id"
        cursor.execute(query, params)

        copy_map: dict[int, List[CopyInfo]] = {}

        rows = cursor.fetchall()
        for row in rows:
            copy_info = CopyInfo(
                    id=row[0],
                    status=row[2],
                    created_at=row[3]
                )
            if row[1] in copy_map.keys():
                copy_map[row[1]].append(copy_info)
                continue
            copy_map[row[1]] = [copy_info]

        return copy_map

    @staticmethod
    def _get_active_borrowings(cursor, book_id: Optional[int] = None) -> Dict[int, List[BorrowedCopyInfo]]:
        """Get active borrowings with optional filtering by book ID"""
        query = f"""
                SELECT c.book_id, b.title, br.copy_id, br.user_id, br.borrowed_at, br.due_date,
                       u.first_name, u.last_name, u.email,
                       CASE WHEN br.due_date < CURRENT_DATE THEN true ELSE false END as is_overdue
                FROM {BORROWINGS_TABLE_NAME} br
                LEFT JOIN {COPIES_TABLE_NAME} c ON br.copy_id = c.id
                LEFT JOIN {USERS_TABLE_NAME} u ON br.user_id = u.id
                LEFT JOIN {BOOKS_TABLE_NAME} b ON c.book_id = b.id
                WHERE br.returned_at IS NULL
            """
        params = ()

        if book_id is not None:
            query += " AND c.book_id = %s"
            params = (book_id,)

        query += " ORDER BY c.book_id, br.due_date"
        cursor.execute(query, params)

        borrow_copy_map: Dict[int, List[BorrowedCopyInfo]] = {}

        for row in cursor.fetchall():
            borrowed_copy_info = BorrowedCopyInfo(
                                    book_title=row[1],
                                    copy_id=row[2],
                                    borrower_id=row[3],
                                    borrowed_at=row[4],
                                    due_date=row[5],
                                    borrower_first_name=row[6],
                                    borrower_last_name=row[7],
                                    borrower_email=row[8],
                                    is_overdue=row[9],
                                )
            if row[0] in borrow_copy_map.keys():
                borrow_copy_map[row[1]].append(borrowed_copy_info)
                continue
            borrow_copy_map[row[0]] = [borrowed_copy_info]

        return borrow_copy_map


    @staticmethod
    def _merge_book_data(books: List[BaseBook], copies: Dict[int, List[CopyInfo]], borrowings: Dict[int, List[BorrowedCopyInfo]]) -> List[BookWithCopies]:
        """Merge books, copies and borrowings data into BookWithCopies objects"""
        books = [
            BookWithCopies(
                id=b.id,
                title=b.title,
                isbn=b.isbn,
                year_published=b.year_published,
                available_copies=copies.get(b.id, []),
                borrowed_copies= borrowings.get(b.id, [])
            )
            for b in books
        ]

        return books

    async def get_all_books_with_copies(self) -> List[BookWithCopies]:
        """Get all books with copy information - three separate queries in one transaction"""
        try:
            log_debug(logger, "Fetching all books with copies")

            with DatabaseConnection() as conn:
                with conn:
                    with conn.cursor() as cursor:
                        books = self._get_books(cursor)
                        copies = self._get_copies(cursor)
                        borrowings = self._get_active_borrowings(cursor)
                        result = self._merge_book_data(books, copies, borrowings)
                        log_debug(logger, f"Retrieved {len(result)} books with copies")
                        return result

        except Exception as e:
            log_error(logger, f"Failed to fetch books: {e}", exc_info=e)
            raise

    async def get_book_by_id(self, book_id: int) -> Optional[BookWithCopies]:
        """Get book by ID with copy details - three separate queries in one transaction"""
        try:
            log_debug(logger, f"Fetching book {book_id}")

            with DatabaseConnection() as conn:
                with conn:
                    with conn.cursor() as cursor:
                        books = self._get_books(cursor, book_id=book_id)

                        if not books:
                            return None

                        copies = self._get_copies(cursor, book_id=book_id)
                        borrowings = self._get_active_borrowings(cursor, book_id=book_id)
                        result = self._merge_book_data(books, copies, borrowings)

                        log_debug(logger, f"Found book: {result[0].title if result else 'None'}")
                        return result[0] if result else None

        except Exception as e:
            log_error(logger, f"Failed to fetch book {book_id}: {e}", exc_info=e)
            raise

    @staticmethod
    async def borrow_copy(copy_id: int, user_id: int) -> BorrowingResult:
        """Borrow a specific copy for a user"""
        try:
            log_debug(logger, f"Attempting to borrow copy {copy_id} for user {user_id}")
            with DatabaseConnection() as conn:
                with conn:
                    with conn.cursor() as cursor:
                        cursor.execute(f"""
                            SELECT c.id, c.book_id,
                                   CASE WHEN br.id IS NOT NULL THEN true ELSE false END as is_borrowed
                            FROM {COPIES_TABLE_NAME} c
                            LEFT JOIN {BORROWINGS_TABLE_NAME} br ON c.id = br.copy_id AND br.returned_at IS NULL
                            WHERE c.id = %s
                            FOR UPDATE OF c
                        """, (copy_id,))
                        copy_row = cursor.fetchone()

                        if not copy_row:
                            raise ValueError(f"Copy {copy_id} not found")

                        if copy_row[2]:
                            raise ValueError(f"Copy {copy_id} is already borrowed")

                        due_date = date.today() + timedelta(days=30)

                        cursor.execute(f"""
                            INSERT INTO {BORROWINGS_TABLE_NAME} (copy_id, user_id, due_date)
                            VALUES (%s, %s, %s)
                            RETURNING id, borrowed_at
                        """, (copy_id, user_id, due_date))
                        borrowing_row = cursor.fetchone()

                        result = BorrowingResult(
                            borrowing_id=borrowing_row[0],
                            copy_id=copy_id,
                            borrowed_at=borrowing_row[1],
                            due_date=due_date
                        )

                        log_debug(logger, f"Successfully borrowed copy {copy_id}")
                        return result

        except Exception as e:
            log_error(logger, f"Failed to borrow copy {copy_id}: {e}", exc_info=e)
            raise

    @staticmethod
    async def return_book(copy_id: int) -> ReturnResult:
        """Return a book"""
        try:
            log_debug(logger, f"Attempting to return copy {copy_id}")
            with DatabaseConnection() as conn:
                with conn:
                    with conn.cursor() as cursor:
                        return_date = date.today()
                        cursor.execute(f"""
                            UPDATE {BORROWINGS_TABLE_NAME} 
                            SET returned_at = %s 
                            WHERE copy_id = %s AND returned_at IS NULL
                            RETURNING id
                        """, (return_date, copy_id))

                        borrowing_row = cursor.fetchone()
                        if not borrowing_row:
                            raise ValueError(f"No active borrowing found for copy {copy_id}")

                        borrowing_id = borrowing_row[0]

                        result = ReturnResult(
                            borrowing_id=borrowing_id,
                            copy_id=copy_id,
                            returned_at=return_date
                        )

                        log_debug(logger, f"Successfully returned copy {copy_id}")
                        return result

        except Exception as e:
            log_error(logger, f"Failed to return copy {copy_id}: {e}", exc_info=e)
            raise

    async def create_book(self, book_data: Dict[str, Any]) -> BookWithCopies:
        """Create new book with copies"""
        try:
            log_debug(logger, f"Creating book: {book_data.get('title')}")
            with DatabaseConnection() as conn:
                with conn:
                    with conn.cursor() as cursor:
                        cursor.execute(f"""
                            INSERT INTO {BOOKS_TABLE_NAME} (title, isbn, year_published)
                            VALUES (%s, %s, %s)
                            RETURNING id
                        """, (
                            book_data['title'],
                            book_data.get('isbn'),
                            book_data.get('year_published')
                        ))

                        book_id = cursor.fetchone()[0]

                        copies_count = book_data['copies_count']
                        copy_values = [(book_id,) for _ in range(copies_count)]

                        cursor.executemany(f"""
                            INSERT INTO {COPIES_TABLE_NAME} (book_id)
                            VALUES (%s)
                        """, copy_values)

                        log_debug(logger, f"Created book '{book_data['title']}' with {copies_count} copies")

                        return await self.get_book_by_id(book_id)

        except psycopg2.IntegrityError as e:
            if 'unique_isbn' in str(e):
                raise ValueError(f"Book with ISBN '{book_data.get('isbn')}' already exists")
            else:
                raise ValueError(f"Database constraint violation: {e}")
        except Exception as e:
            log_error(logger, f"Failed to create book: {e}", exc_info=e)
            raise
