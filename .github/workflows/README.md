# GitHub Actions CI Workflow

This directory contains the Continuous Integration (CI) workflow for the C# AI Buddy Site repository.

## Workflow: `ci.yml`

The CI workflow validates both Python projects in the repository:

### Projects Validated
- **API Project** (`src/api/`) - FastAPI backend
- **Data Ingestion Project** (`src/dataIngestion/`) - RAG data pipeline

### Validation Steps

1. **Environment Setup**
   - Python 3.12 setup
   - Pip dependency caching
   - Virtual environment creation

2. **Dependency Installation**
   - Install from `requirements.txt` (with timeout and error handling)
   - Continue on failure to prioritize syntax validation

3. **Code Validation**
   - **Syntax validation** using `python -m py_compile` for all modules
   - **Import testing** when dependencies are available
   - **Test file validation** for all Python files in test directories

4. **Test Execution**
   - Run existing test suites when available
   - Continue on test failures (syntax validation is primary goal)

### Triggers
- Push to `main` branch
- Pull requests targeting `main` branch

### Build Status
- Each project builds independently
- Summary job reports overall status
- Graceful failure handling ensures syntax issues are caught even if dependencies fail

This ensures all code can compile and basic functionality works before merging changes.