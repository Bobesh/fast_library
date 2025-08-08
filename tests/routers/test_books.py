import pytest
from unittest.mock import AsyncMock, MagicMock
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
            )
        ]
        override_dependency.get_all_books.return_value = mock_books

        response = client.get("/books/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["title"] == "Test Book 1"
        assert data[0]["total_copies"] == 1
        override_dependency.get_all_books.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_books_empty(self, client, override_dependency):
        override_dependency.get_all_books.return_value = []

        response = client.get("/books/")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 0


class TestGetBook:
    @pytest.mark.asyncio
    async def test_get_book_success(self, client, override_dependency):
        book_id = 1
        mock_book = MockBookWithCopies(
            id=book_id,
            title="Test Book",
            isbn="1234567890123",
            year_published=2023,
            available_copies=[
                MockCopyInfo(id=1, book_id=book_id, created_at=date.today())
            ],
            borrowed_copies=[],
            total_copies=1,
            available_copies_count=1,
            borrowed_copies_count=0,
            is_available=True,
            availability_status="Fully available",
        )
        override_dependency.get_book_details.return_value = mock_book

        response = client.get(f"/books/{book_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == book_id
        assert data["title"] == "Test Book"
        override_dependency.get_book_details.assert_called_once_with(book_id)

    @pytest.mark.asyncio
    async def test_get_book_not_found(self, client, override_dependency):
        book_id = 999
        override_dependency.get_book_details.return_value = None

        response = client.get(f"/books/{book_id}")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "not found" in data["detail"].lower()


class TestBorrowCopy:
    @pytest.mark.asyncio
    async def test_borrow_copy_success(self, client, override_dependency):
        copy_id = 1
        user_id = 123
        mock_result = MockBorrowingResult(
            borrowing_id=1,
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
        assert data["borrowing_details"]["copy_id"] == copy_id
        assert data["borrowing_details"]["borrowing_id"] == 1
        override_dependency.borrow_copy.assert_called_once_with(copy_id, user_id)

    @pytest.mark.asyncio
    async def test_borrow_copy_missing_header(self, client, override_dependency):
        copy_id = 1

        response = client.post(f"/books/copies/{copy_id}/borrow")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_borrow_copy_invalid_copy(self, client, override_dependency):
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
    async def test_borrow_copy_already_borrowed(self, client, override_dependency):
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


class TestReturnBook:
    @pytest.mark.asyncio
    async def test_return_book_success(self, client, override_dependency):
        copy_id = 1
        mock_result = MockReturnResult(
            borrowing_id=1, copy_id=copy_id, returned_at=date.today()
        )
        override_dependency.return_book.return_value = mock_result

        response = client.post(f"/books/copies/{copy_id}/return")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Book returned successfully"
        assert data["return_details"]["copy_id"] == copy_id
        assert data["return_details"]["borrowing_id"] == 1
        assert data["return_details"]["returned_at"] == str(date.today())
        override_dependency.return_book.assert_called_once_with(copy_id)

    @pytest.mark.asyncio
    async def test_return_book_not_borrowed(self, client, override_dependency):
        copy_id = 1
        override_dependency.return_book.side_effect = ValueError(
            "Copy is not currently borrowed"
        )

        response = client.post(f"/books/copies/{copy_id}/return")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Copy is not currently borrowed"

    @pytest.mark.asyncio
    async def test_return_book_invalid_copy(self, client, override_dependency):
        copy_id = 999
        override_dependency.return_book.side_effect = ValueError("Copy not found")

        response = client.post(f"/books/copies/{copy_id}/return")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Copy not found"


class TestCreateBook:
    @pytest.mark.asyncio
    async def test_create_book_success(self, client, override_dependency):
        book_data = {
            "title": "New Test Book",
            "isbn": "1234567890123",
            "year_published": 2023,
            "copies_count": 3,
        }

        mock_created_book = MockBookWithCopies(
            id=1,
            title="New Test Book",
            isbn="1234567890123",
            year_published=2023,
            available_copies=[
                MockCopyInfo(id=1, book_id=1, created_at=date.today()),
                MockCopyInfo(id=2, book_id=1, created_at=date.today()),
                MockCopyInfo(id=3, book_id=1, created_at=date.today()),
            ],
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
        assert data["book"]["id"] == 1
        assert data["book"]["title"] == "New Test Book"
        assert data["book"]["total_copies"] == 3

        call_args = override_dependency.create_book.call_args[0][0]
        assert call_args["title"] == "New Test Book"
        assert call_args["isbn"] == "1234567890123"
        assert call_args["year_published"] == 2023
        assert call_args["copies_count"] == 3

    @pytest.mark.asyncio
    async def test_create_book_minimal_data(self, client, override_dependency):
        book_data = {"title": "Minimal Book", "copies_count": 1}

        mock_created_book = MockBookWithCopies(
            id=1,
            title="Minimal Book",
            isbn=None,
            year_published=None,
            available_copies=[MockCopyInfo(id=1, book_id=1, created_at=date.today())],
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
        data = response.json()
        assert data["book"]["title"] == "Minimal Book"
        assert data["book"]["isbn"] is None
        assert data["book"]["year_published"] is None

    @pytest.mark.asyncio
    async def test_create_book_invalid_title_empty(self, client, override_dependency):
        book_data = {"title": "", "copies_count": 1}

        response = client.post("/books/", json=book_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data

    @pytest.mark.asyncio
    async def test_create_book_invalid_title_too_long(
        self, client, override_dependency
    ):
        book_data = {"title": "a" * 256, "copies_count": 1}  # Too long title

        response = client.post("/books/", json=book_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_book_invalid_copies_count_zero(
        self, client, override_dependency
    ):
        book_data = {"title": "Test Book", "copies_count": 0}

        response = client.post("/books/", json=book_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_book_invalid_copies_count_too_high(
        self, client, override_dependency
    ):
        book_data = {"title": "Test Book", "copies_count": 51}

        response = client.post("/books/", json=book_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_book_invalid_isbn_too_long(self, client, override_dependency):
        book_data = {
            "title": "Test Book",
            "isbn": "12345678901234",
            "copies_count": 1,
        }

        response = client.post("/books/", json=book_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_book_invalid_year_too_low(self, client, override_dependency):
        book_data = {"title": "Test Book", "year_published": 999, "copies_count": 1}

        response = client.post("/books/", json=book_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_book_invalid_year_too_high(self, client, override_dependency):
        book_data = {"title": "Test Book", "year_published": 2031, "copies_count": 1}

        response = client.post("/books/", json=book_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_book_missing_required_fields(
        self, client, override_dependency
    ):
        book_data = {
            "isbn": "1234567890123"
        }

        response = client.post("/books/", json=book_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_create_book_library_manager_error(self, client, override_dependency):
        book_data = {"title": "Test Book", "copies_count": 1}
        override_dependency.create_book.side_effect = ValueError("Database error")

        response = client.post("/books/", json=book_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Database error"

    @pytest.mark.asyncio
    async def test_create_book_duplicate_isbn(self, client, override_dependency):
        book_data = {"title": "Test Book", "isbn": "1234567890123", "copies_count": 1}
        override_dependency.create_book.side_effect = ValueError(
            "Book with this ISBN already exists"
        )

        response = client.post("/books/", json=book_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"] == "Book with this ISBN already exists"


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_invalid_book_id_type(self, client, override_dependency):
        response = client.get("/books/invalid_id")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_invalid_copy_id_type_borrow(self, client, override_dependency):
        response = client.post(
            "/books/copies/invalid_id/borrow", headers={"x-user-Id": "123"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_invalid_copy_id_type_return(self, client, override_dependency):
        response = client.post("/books/copies/invalid_id/return")

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_invalid_user_id_header(self, client, override_dependency):
        response = client.post(
            "/books/copies/1/borrow", headers={"x-user-Id": "invalid_user_id"}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestResponseModels:
    @pytest.mark.asyncio
    async def test_book_with_mixed_availability(self, client, override_dependency):
        book_id = 1
        mock_book = MockBookWithCopies(
            id=book_id,
            title="Mixed Availability Book",
            isbn="1234567890123",
            year_published=2023,
            available_copies=[
                MockCopyInfo(id=1, book_id=book_id, created_at=date.today()),
                MockCopyInfo(id=2, book_id=book_id, created_at=date.today()),
            ],
            borrowed_copies=[
                MockBorrowedCopyInfo(
                    copy_id=3,
                    borrower_id=123,
                    borrower_first_name="John",
                    borrower_last_name="Doe",
                    borrower_email="john@example.com",
                    borrowed_at=date.today() - timedelta(days=5),
                    due_date=date.today() + timedelta(days=9),
                    is_overdue=False,
                    book_title="Mixed Availability Book",
                )
            ],
            total_copies=3,
            available_copies_count=2,
            borrowed_copies_count=1,
            is_available=True,
            availability_status="2 of 3 available",
        )
        override_dependency.get_book_details.return_value = mock_book

        response = client.get(f"/books/{book_id}")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total_copies"] == 3
        assert data["available_copies_count"] == 2
        assert data["borrowed_copies_count"] == 1
        assert data["is_available"] is True
        assert data["availability_status"] == "2 of 3 available"

        borrowed_copy = data["borrowed_copies"][0]
        assert borrowed_copy["borrower_full_name"] == "John Doe"
        assert borrowed_copy["days_until_due"] == 9
