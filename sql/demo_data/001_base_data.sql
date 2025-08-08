INSERT INTO books (title, isbn, year_published) VALUES
    ('The Great Gatsby', '9780743273565', 1925),
    ('To Kill a Mockingbird', '9780061120084', 1960),
    ('1984', '9780451524935', 1949),
    ('Pride and Prejudice', '9780141439518', 1813),
    ('The Catcher in the Rye', '9780316769174', 1951);

INSERT INTO copies (book_id) VALUES
    (1), (1), (1),  -- 3 copies of Gatsby
    (2), (2),       -- 2 copies of Mockingbird
    (3),            -- 1 copy of 1984
    (4), (4), (4),  -- 3 copies of Pride and Prejudice
    (5), (5);       -- 2 copies of Catcher

INSERT INTO users (username, email, first_name, last_name) VALUES
    ('alice_wonder', 'alice@demo.com', 'Alice', 'Wonderland'),
    ('bob_builder', 'bob@demo.com', 'Bob', 'Builder'),
    ('charlie_chocolate', 'charlie@demo.com', 'Charlie', 'Chocolate'),
    ('diana_prince', 'diana@demo.com', 'Diana', 'Prince'),
    ('eve_online', 'eve@demo.com', 'Eve', 'Online');

INSERT INTO borrowings (copy_id, user_id, due_date) VALUES
    (1, 1, CURRENT_DATE + INTERVAL '25 days'), -- Alice borrowed Gatsby
    (4, 2, CURRENT_DATE + INTERVAL '15 days'), -- Bob borrowed Mockingbird
    (6, 3, CURRENT_DATE - INTERVAL '5 days');  -- Charlie has overdue 1984

UPDATE copies SET status = 'borrowed' WHERE id IN (1, 4, 6);

INSERT INTO borrowings (copy_id, user_id, due_date, returned_at) VALUES
    (2, 4, CURRENT_DATE - INTERVAL '20 days', CURRENT_DATE - INTERVAL '18 days'), -- Diana returned Gatsby
    (7, 1, CURRENT_DATE - INTERVAL '35 days', CURRENT_DATE - INTERVAL '30 days'); -- Alice returned Pride & Prejudice