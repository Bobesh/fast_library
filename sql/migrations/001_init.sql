-- Books (titles)
CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    isbn VARCHAR(13) UNIQUE,
    year_published INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Physical copies of books
CREATE TABLE copies (
    id SERIAL PRIMARY KEY,
    book_id INTEGER REFERENCES books(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'available', -- available, borrowed, damaged, lost
    created_at TIMESTAMP DEFAULT NOW()
);

-- Library users/readers
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Borrowing records
CREATE TABLE borrowings (
    id SERIAL PRIMARY KEY,
    copy_id INTEGER REFERENCES copies(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    borrowed_at DATE DEFAULT CURRENT_DATE,
    due_date DATE NOT NULL,
    returned_at DATE NULL,   -- NULL = not returned yet
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_copies_book_status ON copies(book_id, status);
CREATE INDEX idx_borrowings_returned ON borrowings(returned_at) WHERE returned_at IS NULL;
CREATE INDEX idx_borrowings_due_date ON borrowings(due_date);
CREATE UNIQUE INDEX ix_users_username ON users(username);
CREATE UNIQUE INDEX ix_users_email ON users(email);
