import pytest
from unittest.mock import Mock, patch
from datetime import date
import psycopg2

from app.models.books import (
    BookWithCopies,
    BaseBook,
    CopyInfo,
    BorrowedCopyInfo,
    BorrowingResult,
    ReturnResult,
)
from app.services.library_psql import LibraryPsql


class TestLibraryPsql:

    @pytest.fixture
    def library_psql(self):
        """Create LibraryPsql instance"""
        return LibraryPsql()

    @pytest.fixture
    def mock_cursor(self):
        """Mock database cursor"""
        cursor = Mock()
        cursor.fetchall = Mock()
        cursor.fetchone = Mock()
        cursor.execute = Mock()
        return cursor

    @pytest.fixture
    def mock_connection(self, mock_cursor):
        """Mock database connection with cursor"""
        conn = Mock()
        conn.cursor.return_value.__enter__ = Mock(return_value=mock_cursor)
        conn.cursor.return_value.__exit__ = Mock(return_value=None)
        conn.__enter__ = Mock(return_value=conn)
        conn.__exit__ = Mock(return_value=None)
        return conn

    @pytest.fixture
    def sample_books_data(self):
        """Sample books data from database"""
        return [
            (1, "The Hobbit", "9780547928227", 1937),
            (2, "1984", "9780451524935", 1949),
        ]

    @pytest.fixture
    def sample_copies_data(self):
        """Sample copies data from database"""
        return [
            (1, 1, date(2024, 1, 1)),
            (2, 1, date(2024, 1, 1)),
            (3, 2, date(2024, 1, 2)),
        ]

    @pytest.fixture
    def sample_borrowings_data(self):
        """Sample borrowings data from database"""
        return [
            (
                1,
                "The Hobbit",
                1,
                1,
                date(2024, 1, 10),
                date(2024, 2, 10),
                "John",
                "Doe",
                "john@test.com",
                False,
            ),
        ]

    def test_get_books_all(self, mock_cursor, sample_books_data):
        """Test getting all books"""
        mock_cursor.fetchall.return_value = sample_books_data

        result = LibraryPsql._get_books(mock_cursor)

        mock_cursor.execute.assert_called_once()
        assert len(result) == 2
        assert result[0].id == 1
        assert result[0].title == "The Hobbit"
        assert result[1].id == 2
        assert result[1].title == "1984"

    def test_get_books_by_id(self, mock_cursor, sample_books_data):
        """Test getting books by ID"""
        mock_cursor.fetchall.return_value = [sample_books_data[0]]

        result = LibraryPsql._get_books(mock_cursor, book_id=1)

        mock_cursor.execute.assert_called_once()
        assert len(result) == 1
        assert result[0].id == 1
        assert result[0].title == "The Hobbit"

    def test_get_copies_all(self, mock_cursor, sample_copies_data):
        """Test getting all copies"""
        mock_cursor.fetchall.return_value = sample_copies_data

        result = LibraryPsql._get_copies(mock_cursor)

        mock_cursor.execute.assert_called_once()
        assert len(result) == 2
        assert 1 in result
        assert 2 in result
        assert len(result[1]) == 2
        assert len(result[2]) == 1

    def test_get_active_borrowings(self, mock_cursor, sample_borrowings_data):
        """Test getting active borrowings"""
        mock_cursor.fetchall.return_value = sample_borrowings_data

        result = LibraryPsql._get_active_borrowings(mock_cursor)

        mock_cursor.execute.assert_called_once()
        assert len(result) == 1
        assert 1 in result
        borrowing = result[1][0]
        assert borrowing.copy_id == 1
        assert borrowing.borrower_first_name == "John"
        assert borrowing.book_title == "The Hobbit"

    def test_merge_book_data(self):
        """Test merging books, copies and borrowings data"""
        books = [BaseBook(id=1, title="Test Book", isbn="123", year_published=2024)]

        copies = {
            1: [
                CopyInfo(id=1, book_id=1, created_at=date(2024, 1, 1)),
                CopyInfo(id=2, book_id=1, created_at=date(2024, 1, 1)),
            ]
        }

        borrowings = {
            1: [
                BorrowedCopyInfo(
                    book_title="Test Book",
                    copy_id=1,
                    borrower_id=1,
                    borrowed_at=date(2024, 1, 10),
                    due_date=date(2024, 2, 10),
                    borrower_first_name="John",
                    borrower_last_name="Doe",
                    borrower_email="john@test.com",
                    is_overdue=False,
                )
            ]
        }

        result = LibraryPsql._merge_book_data(books, copies, borrowings)

        assert len(result) == 1
        book = result[0]
        assert book.title == "Test Book"
        assert len(book.available_copies) == 1
        assert len(book.borrowed_copies) == 1
        assert book.available_copies[0].id == 2
        assert book.borrowed_copies[0].copy_id == 1

    @pytest.mark.asyncio
    @patch("app.services.library_psql.DatabaseConnection")
    async def test_get_all_books_with_copies(
        self,
        mock_db_connection,
        library_psql,
        mock_connection,
        sample_books_data,
        sample_copies_data,
        sample_borrowings_data,
    ):
        """Test getting all books with copies"""
        mock_db_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_connection.return_value.__exit__ = Mock(return_value=None)

        cursor = mock_connection.cursor.return_value.__enter__.return_value

        cursor.fetchall.side_effect = [
            sample_books_data,
            sample_copies_data,
            sample_borrowings_data,
        ]

        result = await library_psql.get_all_books_with_copies()

        assert len(result) == 2
        assert result[0].title == "The Hobbit"
        assert result[1].title == "1984"
        assert cursor.execute.call_count == 3

    @pytest.mark.asyncio
    @patch("app.services.library_psql.DatabaseConnection")
    async def test_get_book_by_id_found(
        self, mock_db_connection, library_psql, mock_connection, sample_books_data
    ):
        """Test getting book by ID when found"""
        mock_db_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_connection.return_value.__exit__ = Mock(return_value=None)

        cursor = mock_connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.side_effect = [[sample_books_data[0]], [], []]

        result = await library_psql.get_book_by_id(1)

        assert result is not None
        assert result.title == "The Hobbit"
        assert result.id == 1

    @pytest.mark.asyncio
    @patch("app.services.library_psql.DatabaseConnection")
    async def test_get_book_by_id_not_found(
        self, mock_db_connection, library_psql, mock_connection
    ):
        """Test getting book by ID when not found"""
        mock_db_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_connection.return_value.__exit__ = Mock(return_value=None)

        cursor = mock_connection.cursor.return_value.__enter__.return_value
        cursor.fetchall.return_value = []

        result = await library_psql.get_book_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    @patch("app.services.library_psql.DatabaseConnection")
    async def test_borrow_copy_success(self, mock_db_connection, mock_connection):
        """Test successful copy borrowing"""
        mock_db_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_connection.return_value.__exit__ = Mock(return_value=None)

        cursor = mock_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(1, 1, False), (123, date.today())]

        result = await LibraryPsql.borrow_copy(1, 1)

        assert isinstance(result, BorrowingResult)
        assert result.borrowing_id == 123
        assert result.copy_id == 1
        assert cursor.execute.call_count == 2

    @pytest.mark.asyncio
    @patch("app.services.library_psql.DatabaseConnection")
    async def test_borrow_copy_not_found(self, mock_db_connection, mock_connection):
        """Test borrowing non-existent copy"""
        mock_db_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_connection.return_value.__exit__ = Mock(return_value=None)

        cursor = mock_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = None

        with pytest.raises(ValueError, match="Copy 999 not found"):
            await LibraryPsql.borrow_copy(999, 1)

    @pytest.mark.asyncio
    @patch("app.services.library_psql.DatabaseConnection")
    async def test_borrow_copy_already_borrowed(
        self, mock_db_connection, mock_connection
    ):
        """Test borrowing already borrowed copy"""
        mock_db_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_connection.return_value.__exit__ = Mock(return_value=None)

        cursor = mock_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.return_value = (1, 1, True)

        with pytest.raises(ValueError, match="Copy 1 is already borrowed"):
            await LibraryPsql.borrow_copy(1, 1)

    @pytest.mark.asyncio
    @patch("app.services.library_psql.DatabaseConnection")
    async def test_create_book_success(
        self, mock_db_connection, library_psql, mock_connection
    ):
        """Test successful book creation"""
        mock_db_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_connection.return_value.__exit__ = Mock(return_value=None)

        cursor = mock_connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [
            (1, "Test Book", "123", 2024, date.today()),
        ]
        cursor.fetchall.return_value = [(1, date.today()), (2, date.today())]

        book_data = {
            "title": "Test Book",
            "isbn": "123",
            "year_published": 2024,
            "copies_count": 2,
        }

        result = await library_psql.create_book(book_data)

        assert isinstance(result, BookWithCopies)
        assert result.title == "Test Book"
        assert len(result.available_copies) == 2
        assert len(result.borrowed_copies) == 0

    @pytest.mark.asyncio
    @patch("app.services.library_psql.DatabaseConnection")
    async def test_create_book_duplicate_isbn(
        self, mock_db_connection, library_psql, mock_connection
    ):
        """Test creating book with duplicate ISBN"""
        mock_db_connection.return_value.__enter__ = Mock(return_value=mock_connection)
        mock_db_connection.return_value.__exit__ = Mock(return_value=None)

        cursor = mock_connection.cursor.return_value.__enter__.return_value
        cursor.execute.side_effect = psycopg2.IntegrityError(
            "unique_isbn constraint violation"
        )

        book_data = {
            "title": "Test Book",
            "isbn": "123",
            "year_published": 2024,
            "copies_count": 1,
        }

        with pytest.raises(ValueError, match="Book with ISBN '123' already exists"):
            await library_psql.create_book(book_data)
