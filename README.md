# Bacterial Classification System

A machine learning system for classifying bacteria as pathogenic or non-pathogenic based on their characteristics. This project uses data scraped from MiMeDB and applies ensemble learning techniques to differentiate between pathogenic and non-pathogenic bacteria in the human body.

## Features

- **Web Scraper**: Collects bacteria data from MiMeDB
- **Database**: Stores bacteria characteristics with PostgreSQL
- **API**: FastAPI backend with comprehensive endpoints
- **Ensemble Learning**: Uses Random Forest, AdaBoost, and XGBoost for classification
- **Standardized API Responses**: Consistent JSON format with pagination, error handling, and metadata
- **External Database Support**: Works with remote PostgreSQL databases (including Neon)

## Prerequisites

- Docker and Docker Compose
- PostgreSQL (local or remote)
- Python 3.9+

## Quick Start

### 1. Set Up Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your database credentials
nano .env
```

### 2. Start Services

For local development with embedded PostgreSQL:

```bash
# Build and start all services
make build
make up-d
```

For using an external database (like Neon):

```bash
# Start only backend and scraper
make up-no-db
```

### 3. Initialize Database and Collect Data

```bash
# Initialize database schema
make init-db

# Run scraper to collect bacteria data
make scrape-with-options SCRAPER_OPTS="--max-bacteria 25"
```

### 4. Verify Data Collection

```bash
# Check count of bacteria in database
make db-query QUERY="SELECT COUNT(*) FROM bacteria;"

# View sample data
make db-query QUERY="SELECT bacteria_id, name, gram_stain, is_pathogen FROM bacteria LIMIT 5;"
```

### 5. Access API

The API is available at:

- API Base: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

## Docker Compose Profiles

Multiple profiles are available for different deployment scenarios:

- **default**: Run everything (backend, scraper, and postgres)
- **backend-only**: Run only the backend service
- **scraper-only**: Run only the scraper service
- **external-db**: Run backend and scraper with external database

```bash
# Example: Run only the backend
make up-backend

# Run with external database
make up-no-db
```

## Database Operations

```bash
# Access database shell
make db-shell

# Run SQL query
make db-query QUERY="SELECT * FROM bacteria LIMIT 10;"

# Export database to file
make db-dump FILE=backup.sql

# Import from backup
make db-restore FILE=backup.sql
```

## API Endpoints

- `GET /api/v1/bacteria` - List bacteria with filtering and pagination
- `GET /api/v1/bacteria/{bacteria_id}` - Get specific bacterium details
- `POST /api/v1/bacteria` - Create new bacterium record
- `PUT /api/v1/bacteria/{bacteria_id}` - Update bacterium properties
- `DELETE /api/v1/bacteria/{bacteria_id}` - Delete bacterium
- `POST /api/v1/bacteria/{bacteria_id}/predict` - Predict pathogenicity
- `GET /api/v1/bacteria/stats/counts` - Get bacteria statistics

## Using External Database

To use with a cloud database like Neon:

1. Update your `.env` file with external database connection details
2. Start services with the external-db profile: `make up-no-db`
3. Initialize database schema: `make init-db-external`
4. Run scraper: `make scrape`

## Development

### Rebuilding Services

```bash
# Rebuild services with changes
make rebuild
```

### Checking Logs

```bash
# View logs from all services
make logs

# Access specific container
make shell-backend
make shell-scraper
```

### Stopping Services

```bash
# Stop all services
make down

# Clean up volumes and containers
make clean
```

## Authors

- Moh Fairuz Alauddin Yahya - 13522057
- Rayhan Fadhlan Azka - 13522095
- Rayendra Althaf Taraka Noor - 13522107
