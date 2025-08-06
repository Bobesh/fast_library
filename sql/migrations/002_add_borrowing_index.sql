CREATE UNIQUE INDEX idx_unique_active_borrowing
ON borrowings(copy_id)
WHERE returned_at IS NULL;