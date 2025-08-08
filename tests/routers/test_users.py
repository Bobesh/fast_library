import pytest
from unittest.mock import AsyncMock
from datetime import date, timedelta
from fastapi.testclient import TestClient
from fastapi import FastAPI, status
from dataclasses import dataclass
from typing import List, Optional

from app.routers.books import router


@dataclass
class MockCopyInfo:
    id: int
    book_id: int
    created_at: date


@dataclass
class MockBorrowedCopyInfo:
    copy_id: int
    borrower_id: int
    borrower_first_name: str
    borrower_last_name: str
    borrower_email: str
    borrowed_at: date
    due_date: date
    is_overdue: bool
    book_title: str


@dataclass
class MockBookWithCopies:
    id: int
    title: str
    isbn: Optional[str]
    year_published: Optional[int]
    available_copies: List[MockCopyInfo]
    borrowed_copies: List[MockBorrowedCopyInfo]
    total_copies: int
    available_copies_count: int
    borrowed_copies_count: int
    is_available: bool
    availability_status: str


@dataclass
class MockBorrowingResult:
    borrowing_id: int
    copy_id: int
    borrowed_at: date
    due_date: date


@dataclass
class MockReturnResult:
    borrowing_id: int
    copy_id: int
    returned_at: date


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(router, prefix="/books")
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_library_manager():
    return AsyncMock()


@pytest.fixture
def override_dependency(app, mock_library_manager):
    from app.core.dependencies import library_manager_dependency

    app.dependency_overrides[library_manager_dependency] = lambda: mock_library_manager
    yield mock_library_manager
    app.dependency_overrides = {}


class TestGetBooks:
    @pytest.mark.asyncio
    async def test_get_books_success(self, client, override_dependency):
        """Test successful retrieval of all books"""
        mock_books = [
            MockBookWithCopies(
                id=1,
                title="Test Book 1",
                isbn="1234567890123",
                year_published=2023,
                available_copies=[
                    MockCopyInfo(id=1, book_id=1, created_at=date.today())
                ],
                borrowed_copies=[],
                total_copies=1,
                available_copies_count=1,
                borrowed_copies_count=0,
                is_available=True,
                availability_status="Fully available",
            ),
            MockBookWithCopies(
                id=2,
                title="Test Book 2",
                isbn=None,
                year_published=None,
                available_copies=[],
                borrowed_copies=[
                    MockBorrowedCopyInfo(
                        copy_id=2,
                        borrower_id=123,
                        borrower_first_name="John",
                        borrower_last_name="Doe",
                        borrower_email="john@example.com",
                        borrowed_at=date.today(),
                        due_date=date.today() + timedelta(days=14),
                        is_overdue=False,
                        book_title="Test Book 2",
                    )
                ],
                total_copies=1,
                available_copies_count=0,
                borrowed_copies_count=1,
                is_available=False,
                availability_status="Not available",
            ),
        ]
        override_dependency.get_all_books.return_value = mock_books

        response = client.get("/books/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2

        assert data[0]["id"] == 1
        assert data[0]["title"] == "Test Book 1"
        assert data[0]["isbn"] == "1234567890123"
        assert data[0]["total_copies"] == 1
        assert data[0]["is_available"] is True

        assert data[1]["id"] == 2
        assert data[1]["title"] == "Test Book 2"
        assert data[1]["isbn"] is None
        assert data[1]["total_copies"] == 1
        assert data[1]["is_available"] is False

        override_dependency.get_all_books.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_books_empty_list(self, client, override_dependency):
        """Test getting books when no books exist"""
        override_dependency.get_all_books.return_value = []

        response = client.get("/books/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0
        override_dependency.get_all_books.assert_called_once()


class TestGetBook:
    @pytest.mark.asyncio
    async def test_get_book_success(self, client, override_dependency):
        """Test successful retrieval of a specific book"""
        book_id = 1
        mock_book = MockBookWithCopies(
            id=book_id,
            title="Specific Book",
            isbn="9876543210123",
            year_published=2022,
            available_copies=[
                MockCopyInfo(id=1, book_id=book_id, created_at=date.today()),
                MockCopyInfo(id=2, book_id=book_id, created_at=date.today()),
            ],
            borrowed_copies=[],
            total_copies=2,
            available_copies_count=2,
            borrowed_copies_count=0,
            is_available=True,
            availability_status="Fully available",
        )
        override_dependency.get_book_details.return_value = mock_book

        response = client.get(f"/books/{book_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == book_id
        assert data["title"] == "Specific Book"
        assert data["isbn"] == "9876543210123"
        assert data["year_published"] == 2022
        assert data["total_copies"] == 2
        assert data["available_copies_count"] == 2
        assert data["borrowed_copies_count"] == 0
        override_dependency.get_book_details.assert_called_once_with(book_id)

    @pytest.mark.asyncio
    async def test_get_book_not_found(self, client, override_dependency):
        """Test getting book that doesn't exist"""
        book_id = 999
        override_dependency.get_book_details.return_value = None

        response = client.get(f"/books/{book_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert f"Book with ID {book_id} not found" in data["detail"]
        override_dependency.get_book_details.assert_called_once_with(book_id)

    @pytest.mark.asyncio
    async def test_get_book_invalid_id_type(self, client, override_dependency):
        """Test getting book with invalid ID type"""
        response = client.get("/books/invalid_id")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestBorrowCopy:
    @pytest.mark.asyncio
    async def test_borrow_copy_success(self, client, override_dependency):
        """Test successful borrowing of a book copy"""
        copy_id = 1
        user_id = 123
        mock_result = MockBorrowingResult(
            borrowing_id=456,
            copy_id=copy_id,
            borrowed_at=date.today(),
            due_date=date.today() + timedelta(days=14),
        )
        override_dependency.borrow_copy.return_value = mock_result

        response = client.post(
            f"/books/copies/{copy_id}/borrow", headers={"x-user-Id": str(user_id)}
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Copy borrowed successfully"
        assert data["borrowing_details"]["borrowing_id"] == 456
        assert data["borrowing_details"]["copy_id"] == copy_id
        assert data["borrowing_details"]["borrowed_at"] == str(date.today())
        assert data["borrowing_details"]["due_date"] == str(
            date.today() + timedelta(days=14)
        )
        override_dependency.borrow_copy.assert_called_once_with(copy_id, user_id)

    @pytest.mark.asyncio
    async def test_borrow_copy_missing_header(self, client, override_dependency):
        """Test borrowing copy without required user header"""
        copy_id = 1

        response = client.post(f"/books/copies/{copy_id}/borrow")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_borrow_copy_invalid_user_header(self, client, override_dependency):
        """Test borrowing copy with invalid user header"""
        copy_id = 1

        response = client.post(
            f"/books/copies/{copy_id}/borrow", headers={"x-user-Id": "invalid"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_borrow_copy_value_error(self, client, override_dependency):
        """Test borrowing copy when business logic raises ValueError"""
        copy_id = 1
        user_id = 123
        override_dependency.borrow_copy.side_effect = ValueError(
            "Copy is already borrowed"
        )

        response = client.post(
            f"/books/copies/{copy_id}/borrow", headers={"x-user-Id": str(user_id)}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Copy is already borrowed"

    @pytest.mark.asyncio
    async def test_borrow_copy_copy_not_found(self, client, override_dependency):
        """Test borrowing non-existent copy"""
        copy_id = 999
        user_id = 123
        override_dependency.borrow_copy.side_effect = ValueError("Copy not found")

        response = client.post(
            f"/books/copies/{copy_id}/borrow", headers={"x-user-Id": str(user_id)}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Copy not found"

    @pytest.mark.asyncio
    async def test_borrow_copy_invalid_copy_id_type(self, client, override_dependency):
        """Test borrowing copy with invalid copy ID type"""
        response = client.post(
            "/books/copies/invalid/borrow", headers={"x-user-Id": "123"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestReturnBook:
    @pytest.mark.asyncio
    async def test_return_book_success(self, client, override_dependency):
        """Test successful return of a book copy"""
        copy_id = 1
        mock_result = MockReturnResult(
            borrowing_id=456, copy_id=copy_id, returned_at=date.today()
        )
        override_dependency.return_book.return_value = mock_result

        response = client.post(f"/books/copies/{copy_id}/return")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Book returned successfully"
        assert data["return_details"]["borrowing_id"] == 456
        assert data["return_details"]["copy_id"] == copy_id
        assert data["return_details"]["returned_at"] == str(date.today())
        override_dependency.return_book.assert_called_once_with(copy_id)

    @pytest.mark.asyncio
    async def test_return_book_not_borrowed(self, client, override_dependency):
        """Test returning book that is not currently borrowed"""
        copy_id = 1
        override_dependency.return_book.side_effect = ValueError(
            "Copy is not currently borrowed"
        )

        response = client.post(f"/books/copies/{copy_id}/return")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Copy is not currently borrowed"

    @pytest.mark.asyncio
    async def test_return_book_copy_not_found(self, client, override_dependency):
        """Test returning non-existent copy"""
        copy_id = 999
        override_dependency.return_book.side_effect = ValueError("Copy not found")

        response = client.post(f"/books/copies/{copy_id}/return")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Copy not found"

    @pytest.mark.asyncio
    async def test_return_book_invalid_copy_id_type(self, client, override_dependency):
        """Test returning book with invalid copy ID type"""
        response = client.post("/books/copies/invalid/return")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCreateBook:
    @pytest.mark.asyncio
    async def test_create_book_success_full_data(self, client, override_dependency):
        """Test successful book creation with all data"""
        book_data = {
            "title": "New Test Book",
            "isbn": "1234567890123",
            "year_published": 2023,
            "copies_count": 3,
        }

        mock_created_book = MockBookWithCopies(
            id=10,
            title="New Test Book",
            isbn="1234567890123",
            year_published=2023,
            available_copies=[MockCopyInfo(id=1, book_id=10, created_at=date.today())],
            borrowed_copies=[],
            total_copies=3,
            available_copies_count=3,
            borrowed_copies_count=0,
            is_available=True,
            availability_status="Fully available",
        )
        override_dependency.create_book.return_value = mock_created_book

        response = client.post("/books/", json=book_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert (
            data["message"] == "Book 'New Test Book' created successfully with 3 copies"
        )
        assert data["book"]["id"] == 10
        assert data["book"]["title"] == "New Test Book"
        override_dependency.create_book.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_book_minimal_data(self, client, override_dependency):
        """Test book creation with minimal required data"""
        book_data = {"title": "Minimal Book", "copies_count": 1}
        mock_created_book = MockBookWithCopies(
            id=11,
            title="Minimal Book",
            isbn=None,
            year_published=None,
            available_copies=[],
            borrowed_copies=[],
            total_copies=1,
            available_copies_count=1,
            borrowed_copies_count=0,
            is_available=True,
            availability_status="Fully available",
        )
        override_dependency.create_book.return_value = mock_created_book

        response = client.post("/books/", json=book_data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["book"]["isbn"] is None

    @pytest.mark.asyncio
    async def test_create_book_value_error(self, client, override_dependency):
        """Test book creation when manager raises ValueError"""
        book_data = {"title": "Test Book", "copies_count": 1}
        override_dependency.create_book.side_effect = ValueError("ISBN already exists")

        response = client.post("/books/", json=book_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "ISBN already exists"

    @pytest.mark.asyncio
    async def test_create_book_validation_errors(self, client, override_dependency):
        """Test validation errors for book creation"""
        invalid_cases = [
            ({"title": "", "copies_count": 1}, 422),
            ({"title": "Test"}, 422),
            ({"title": "Test", "copies_count": 0}, 422),
            ({"title": "Test", "copies_count": 51}, 422),
            (
                {"title": "Test", "year_published": 999, "copies_count": 1},
                422,
            ),
        ]

        for book_data, expected_status in invalid_cases:
            response = client.post("/books/", json=book_data)
            assert response.status_code == expected_status


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_invalid_id_types(self, client, override_dependency):
        """Test invalid ID type handling across endpoints"""
        response = client.get("/books/invalid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        response = client.post(
            "/books/copies/invalid/borrow", headers={"x-user-Id": "123"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        response = client.post("/books/copies/invalid/return")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
