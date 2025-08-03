from typing import List, Optional, Dict, Any
from app.core.database import DatabaseConnection


class Book:
    def __init__(self, id: int, name: str,
                 year: int, isbn: str):
        self.id = id
        self.name = name
        self.year = year
        self.isbn = isbn

    @classmethod
    def get_all(cls) -> List['Book']:
        with DatabaseConnection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, name, year, isbn 
                    FROM books ORDER BY id
                """)
                rows = cursor.fetchall()
                return [cls(*row) for row in rows]

    @classmethod
    def get_by_id(cls, id: int) -> Optional['Book']:
        with DatabaseConnection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id, nazev, isbn, autor_id, rok_vydani, stav 
                    FROM books WHERE id = %s
                """, (id,))
                row = cursor.fetchone()
                return cls(*row) if row else None


    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'year': self.year,
            'isbn': self.isbn
        }
