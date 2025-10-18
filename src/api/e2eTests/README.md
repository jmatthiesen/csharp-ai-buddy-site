# End-to-End Integration Tests

This folder contains end-to-end integration tests that test the real functionality of the API endpoints, including actual database interactions.

## Requirements

- MongoDB connection (local or remote)
- pytest
- pytest-asyncio
- All API dependencies (see `requirements.txt`)

## Setup

1. Install test dependencies:
```bash
pip install pytest pytest-asyncio
```

2. Set up environment variables for MongoDB connection:
```bash
export MONGODB_URI="mongodb://localhost:27017"  # or your MongoDB connection string
export DATABASE_NAME="your_database_name"
```

## Running the Tests

Run all e2e tests:
```bash
cd src/api
pytest e2eTests/ -v
```

Run a specific test file:
```bash
cd src/api
pytest e2eTests/test_news_e2e.py -v
```

Run with output shown (useful for debugging):
```bash
cd src/api
pytest e2eTests/test_news_e2e.py -v -s
```

## Test Data

The e2e tests create test data in the database before running and clean it up after completion. Test documents are identified by:
- IDs starting with `e2e-test-`
- Titles containing "E2E Test"

The cleanup process ensures no test data is left in the database after the tests complete.

## Skipping Tests

If MongoDB environment variables are not set, the tests will be automatically skipped with a message:
```
SKIPPED - MongoDB not configured - set MONGODB_URI and DATABASE_NAME to run e2e tests
```

## What is Tested

### News Endpoint E2E Tests (`test_news_e2e.py`)

1. **Sorting Verification**: Tests that news items are returned sorted by `publishedDate` in descending order (newest first)
2. **Search Functionality**: Tests that search queries work correctly
3. **Pagination**: Tests that pagination parameters are respected
4. **RSS Feed**: Tests that the RSS feed endpoint returns properly formatted data

## Differences from Unit Tests

- **Unit tests** (`tests/` folder) use mocks and test individual components in isolation
- **E2E tests** (`e2eTests/` folder) test the entire system flow including database operations

Both types of tests are important for ensuring code quality and functionality.
