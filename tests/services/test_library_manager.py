import logging
from http.client import HTTPException

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import date

from app.services.library_manager import LibraryManager
from app.models.books import BookWithCopies, BorrowingResult, ReturnResult, CopyInfo
from app.services.library_psql import LibraryPsql


class TestLibraryManager:

    @pytest.fixture
    def mock_library_psql(self):
        """Mock LibraryPsql data access layer"""
        mock = Mock(spec=LibraryPsql)
        mock.get_all_books_with_copies = AsyncMock()
        mock.get_book_by_id = AsyncMock()
        mock.borrow_copy = AsyncMock()
        mock.return_book = AsyncMock()
        mock.create_book = AsyncMock()
        return mock

    @pytest.fixture
    def library_manager(self, mock_library_psql):
        """Create LibraryManager with mocked data access"""
        return LibraryManager(mock_library_psql)

    @pytest.fixture
    def sample_book(self):
        """Sample BookWithCopies for testing"""
        return BookWithCopies(
            id=1,
            title="Test Book",
            isbn="1234567890",
            year_published=2024,
            available_copies=[
                CopyInfo(id=1, book_id=1, created_at=date.today()),
                CopyInfo(id=2, book_id=1, created_at=date.today()),
            ],
            borrowed_copies=[],
        )

    @pytest.fixture
    def sample_borrowing_result(self):
        """Sample BorrowingResult for testing"""
        return BorrowingResult(
            borrowing_id=123, copy_id=1, borrowed_at=date.today(), due_date=date.today()
        )

    @pytest.fixture
    def sample_return_result(self):
        """Sample ReturnResult for testing"""
        return ReturnResult(borrowing_id=123, copy_id=1, returned_at=date.today())

    @pytest.mark.asyncio
    async def test_get_all_books_success(
        self, library_manager, mock_library_psql, sample_book
    ):
        """Test successful retrieval of all books"""
        mock_library_psql.get_all_books_with_copies.return_value = [sample_book]

        result = await library_manager.get_all_books()

        assert len(result) == 1
        assert result[0].title == "Test Book"
        mock_library_psql.get_all_books_with_copies.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_books_empty(self, library_manager, mock_library_psql):
        """Test retrieval when no books exist"""
        mock_library_psql.get_all_books_with_copies.return_value = []

        result = await library_manager.get_all_books()

        assert result == []
        mock_library_psql.get_all_books_with_copies.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_book_details_found(
        self, library_manager, mock_library_psql, sample_book
    ):
        """Test successful retrieval of book details"""
        mock_library_psql.get_book_by_id.return_value = sample_book

        result = await library_manager.get_book_details(1)

        assert result.title == "Test Book"
        assert result.id == 1
        mock_library_psql.get_book_by_id.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_get_book_details_not_found(self, library_manager, mock_library_psql):
        """Test retrieval when book doesn't exist"""
        mock_library_psql.get_book_by_id.return_value = None

        result = await library_manager.get_book_details(999)

        assert result is None
        mock_library_psql.get_book_by_id.assert_called_once_with(999)

    @pytest.mark.asyncio
    async def test_borrow_copy_success(
        self, library_manager, mock_library_psql, sample_borrowing_result
    ):
        """Test successful copy borrowing"""
        mock_library_psql.borrow_copy.return_value = sample_borrowing_result

        result = await library_manager.borrow_copy(1, 1)

        assert isinstance(result, BorrowingResult)
        assert result.borrowing_id == 123
        assert result.copy_id == 1
        mock_library_psql.borrow_copy.assert_called_once_with(1, 1)

    @pytest.mark.asyncio
    async def test_borrow_copy_value_error(self, library_manager, mock_library_psql):
        """Test borrowing when copy is not available"""
        mock_library_psql.borrow_copy.side_effect = ValueError(
            "Copy 1 is already borrowed"
        )

        with pytest.raises(ValueError, match="Copy 1 is already borrowed"):
            await library_manager.borrow_copy(1, 1)

        mock_library_psql.borrow_copy.assert_called_once_with(1, 1)

    @pytest.mark.asyncio
    async def test_borrow_copy_unexpected_error(
        self, library_manager, mock_library_psql
    ):
        """Test borrowing with unexpected error"""
        from fastapi import HTTPException

        mock_library_psql.borrow_copy.side_effect = Exception(
            "Database connection failed"
        )

        with pytest.raises(HTTPException) as exc_info:
            await library_manager.borrow_copy(1, 1)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to process borrowing request"
        mock_library_psql.borrow_copy.assert_called_once_with(1, 1)

    @pytest.mark.asyncio
    async def test_return_book_success(
        self, library_manager, mock_library_psql, sample_return_result
    ):
        """Test successful book return"""
        mock_library_psql.return_book.return_value = sample_return_result

        result = await library_manager.return_book(1)

        assert isinstance(result, ReturnResult)
        assert result.borrowing_id == 123
        assert result.copy_id == 1
        mock_library_psql.return_book.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_return_book_value_error(self, library_manager, mock_library_psql):
        """Test returning when no active borrowing exists"""
        mock_library_psql.return_book.side_effect = ValueError(
            "No active borrowing found for copy 1"
        )

        with pytest.raises(ValueError, match="No active borrowing found for copy 1"):
            await library_manager.return_book(1)

        mock_library_psql.return_book.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_create_book_success(
        self, library_manager, mock_library_psql, sample_book
    ):
        """Test successful book creation"""
        book_data = {
            "title": "Test Book",
            "isbn": "1234567890",
            "year_published": 2024,
            "copies_count": 2,
        }
        mock_library_psql.create_book.return_value = sample_book

        result = await library_manager.create_book(book_data)

        assert isinstance(result, BookWithCopies)
        assert result.title == "Test Book"
        assert result.id == 1
        mock_library_psql.create_book.assert_called_once_with(book_data)

    @pytest.mark.asyncio
    async def test_create_book_duplicate_isbn(self, library_manager, mock_library_psql):
        """Test creating book with duplicate ISBN"""
        book_data = {
            "title": "Test Book",
            "isbn": "1234567890",
            "year_published": 2024,
            "copies_count": 2,
        }
        mock_library_psql.create_book.side_effect = ValueError(
            "Book with ISBN '1234567890' already exists"
        )

        with pytest.raises(
            ValueError, match="Book with ISBN '1234567890' already exists"
        ):
            await library_manager.create_book(book_data)

        mock_library_psql.create_book.assert_called_once_with(book_data)

    @pytest.mark.asyncio
    async def test_create_book_unexpected_error(
        self, library_manager, mock_library_psql
    ):
        """Test creating book with unexpected error"""
        from fastapi.exceptions import HTTPException

        book_data = {
            "title": "Test Book",
            "isbn": "1234567890",
            "year_published": 2024,
            "copies_count": 2,
        }
        mock_library_psql.create_book.side_effect = Exception(
            "Database connection failed"
        )

        with pytest.raises(HTTPException) as exc_info:
            await library_manager.create_book(book_data)

        assert exc_info.value.status_code == 500
        assert exc_info.value.detail == "Failed to create book"
        mock_library_psql.create_book.assert_called_once_with(book_data)

    @pytest.mark.asyncio
    async def test_full_workflow_simulation(
        self,
        library_manager,
        mock_library_psql,
        sample_book,
        sample_borrowing_result,
        sample_return_result,
    ):
        """Test simulated workflow: get books -> borrow -> return"""

        mock_library_psql.get_all_books_with_copies.return_value = [sample_book]
        mock_library_psql.borrow_copy.return_value = sample_borrowing_result
        mock_library_psql.return_book.return_value = sample_return_result

        books = await library_manager.get_all_books()
        assert len(books) == 1

        borrow_result = await library_manager.borrow_copy(1, 1)
        assert borrow_result.copy_id == 1

        return_result = await library_manager.return_book(1)
        assert return_result.copy_id == 1

        mock_library_psql.get_all_books_with_copies.assert_called_once()
        mock_library_psql.borrow_copy.assert_called_once_with(1, 1)
        mock_library_psql.return_book.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_manager_logs_errors(
        self, library_manager, mock_library_psql, caplog
    ):
        """Test that manager properly logs errors"""
        mock_library_psql.borrow_copy.side_effect = ValueError("Test error")

        with caplog.at_level(logging.ERROR, logger="app.services.library_manager"):
            with pytest.raises(ValueError):
                await library_manager.borrow_copy(1, 1)

        assert "LibraryManager: Borrowing failed - Test error" in caplog.text
        assert "ERROR" in caplog.text

    @pytest.mark.asyncio
    async def test_manager_logs_info_on_success(
        self, library_manager, mock_library_psql, sample_borrowing_result, caplog
    ):
        """Test that manager logs success operations"""
        mock_library_psql.borrow_copy.return_value = sample_borrowing_result

        with caplog.at_level(logging.INFO, logger="app.services.library_manager"):
            await library_manager.borrow_copy(1, 1)

        assert "LibraryManager: User 1 attempting to borrow book 1" in caplog.text
        assert (
            "LibraryManager: Successfully processed borrowing for user 1" in caplog.text
        )
        assert "INFO" in caplog.text

    @pytest.mark.asyncio
    async def test_manager_logs_unexpected_errors(
        self, library_manager, mock_library_psql, caplog
    ):
        """Test that manager logs unexpected errors with exc_info"""
        unexpected_error = Exception("Database connection failed")
        mock_library_psql.borrow_copy.side_effect = unexpected_error

        with caplog.at_level(logging.ERROR, logger="app.services.library_manager"):
            with pytest.raises(Exception):
                await library_manager.borrow_copy(1, 1)

        assert (
            "LibraryManager: Unexpected error during borrowing - Database connection failed"
            in caplog.text
        )
        assert "ERROR" in caplog.text

    @pytest.mark.asyncio
    async def test_manager_logs_debug_messages(
        self, library_manager, mock_library_psql, sample_book, caplog
    ):
        """Test that manager logs debug messages"""
        mock_library_psql.get_all_books_with_copies.return_value = [sample_book]

        with caplog.at_level(logging.DEBUG, logger="app.services.library_manager"):
            await library_manager.get_all_books()

        assert "LibraryManager: Getting all books" in caplog.text
        assert "DEBUG" in caplog.text

    @pytest.mark.asyncio
    async def test_create_book_logs_creation(
        self, library_manager, mock_library_psql, sample_book, caplog
    ):
        """Test that book creation is properly logged"""

        book_data = {"title": "New Book", "copies_count": 2}
        mock_library_psql.create_book.return_value = sample_book

        with caplog.at_level(logging.INFO, logger="app.services.library_manager"):
            await library_manager.create_book(book_data)

        assert "LibraryManager: Creating book 'New Book'" in caplog.text
        assert (
            "LibraryManager: Successfully created book 'Test Book' with ID 1"
            in caplog.text
        )

    @pytest.mark.asyncio
    async def test_return_book_logs_operation(
        self, library_manager, mock_library_psql, sample_return_result, caplog
    ):
        """Test that book return is properly logged"""
        mock_library_psql.return_book.return_value = sample_return_result

        with caplog.at_level(logging.INFO, logger="app.services.library_manager"):
            await library_manager.return_book(1)

        assert "LibraryManager: Attempting to return copy 1" in caplog.text
        assert "LibraryManager: Successfully processed return for copy 1" in caplog.text
