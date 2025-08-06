INSERT INTO users (username, email, first_name, last_name, phone) VALUES
    ('alice_wonder', 'alice@demo.com', 'Alice', 'Wonderland', '+420111222333'),
    ('bob_builder', 'bob@demo.com', 'Bob', 'Builder', '+420444555666'),
    ('charlie_chocolate', 'charlie@demo.com', 'Charlie', 'Chocolate', NULL),
    ('diana_prince', 'diana@demo.com', 'Diana', 'Prince', '+420777888999'),
    ('eve_online', 'eve@demo.com', 'Eve', 'Online', '+420123987654');

INSERT INTO borrowings (copy_id, user_id, due_date) VALUES
    (1, 1, CURRENT_DATE + INTERVAL '5 days'),

    (3, 2, CURRENT_DATE - INTERVAL '3 days'),

    (5, 3, CURRENT_DATE + INTERVAL '20 days');

UPDATE copies SET status = 'borrowed' WHERE id IN (1, 3, 5);

-- Add some borrowing history (returned books)
INSERT INTO borrowings (copy_id, user_id, due_date, returned_at) VALUES
    (2, 4, CURRENT_DATE - INTERVAL '10 days', CURRENT_DATE - INTERVAL '8 days'),

    (6, 1, CURRENT_DATE - INTERVAL '25 days', CURRENT_DATE - INTERVAL '20 days'),

    (4, 5, CURRENT_DATE - INTERVAL '15 days', CURRENT_DATE - INTERVAL '18 days'),

    (7, 2, CURRENT_DATE - INTERVAL '35 days', CURRENT_DATE - INTERVAL '32 days');