# Fast Library - Library Management System

A library management system for handling book loans. Manages books, their copies, and users.

## Technologies

- **Python 3.12+** with FastAPI framework
- **PostgreSQL** as database
- **Poetry** for dependency management
- **Docker** for containerization

## Database

Uses PostgreSQL as database. Migrations are stored in the `sql/` folder, along with dummy data for local development.

## Authentication

Authentication is done via API key, which is a simple approach since we don't expect the application to be exposed to the internet and covered by SSO for example.

## Installation and Running

### Local Development

1. **Install dependencies:**
   ```bash
   poetry install
2. **Start database:**
    ```bash
   docker compose up
3. **Run application:**
    ```bash
   poetry run python -m app.main
   
### Docker application + database
1. **Start entire application:**
    ```bash
    docker-compose -f docker-compose.app.yml up --build

2. **Run in background:**
    ```bash
    docker-compose -f docker-compose.app.yml up -d --build

3. **Stop:**
    ```bash
    docker-compose -f docker-compose.app.yml down
   
### Development tools
1. **Check formatting:**
    ```bash
    poetry run black --check --diff .

2. **Apply formatting:**
    ```bash
    poetry run black .
   
3. **Check types:**
    ```bash
    poetry run mypy app/

4. **Tests:**
    ```
    poetry run pytest
   
## Project Structure

fast_library/
├── app/              
│   ├── core/      
│   ├── models/         
│   ├── routers/        
│   └── services/          
├── sql/                 
│   ├── migrations/      
│   └── demo_data/       
├── tests/               
├── docker-compose.yml   
├── docker-compose.app.yml 
└── pyproject.toml

## API Usage

All protected endpoints require API key in header:

```bash
# Get all books
curl -H "X-API-Key: your-api-key" http://0.0.0.0:8000/api/books/

# Borrow a book
curl -X POST \\
  -H "X-API-Key: your-api-key" \\
  -H "x-user-Id: 1" \\
  http://0.0.0.0:8000/api/books/copies/1/borrow

# Create new book
curl -X POST \\
  -H "X-API-Key: your-api-key" \\
  -H "Content-Type: application/json" \\
  -d '{"title": "New Book", "copies_count": 3}' \\
  http://0.0.0.0:8000/api/books/
 ```

## Configuration
Application uses environment variables for configuration. Default values are set for local development.

Key variables:

DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD - there are defaults in app

API_KEY - for authentication
