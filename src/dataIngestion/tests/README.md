# RAG Data Ingestion Pipeline - Test Suite

This directory contains tests for the RAG Data Ingestion Pipeline, focusing on validating the AI-powered framework categorization functionality.

## Test Structure

### Core Test Files

- **`test_ai_categorization.py`** - Main test suite for AI categorization logic
- **`test_config.py`** - Test configuration and sample data
- **`run_tests.py`** - Test runner script
- **`__init__.py`** - Python package initialization

## Test Categories

### 1. Mock Tests (Always Run)
These tests use mocked OpenAI responses and don't require an API key:

- **Framework Categories Test** - Validates all expected framework categories are available
- **Semantic Kernel Categorization** - Tests basic Semantic Kernel detection
- **Semantic Kernel Agents Categorization** - Tests Semantic Kernel family logic
- **ML.NET Categorization** - Tests ML.NET framework detection
- **Tag Validation** - Tests framework tag validation logic
- **Error Handling** - Tests OpenAI API error handling
- **Empty Content Handling** - Tests edge cases with minimal content

### 2. OpenAI Evaluation Tests (Optional)
These tests use the actual OpenAI API and require an API key:

- **Real Semantic Kernel Categorization** - Tests with real OpenAI API
- **Real ML.NET Categorization** - Tests with real OpenAI API  
- **Real Semantic Kernel Agents Categorization** - Tests Semantic Kernel family with real API

## Running Tests

### Prerequisites

1. **Install dependencies:**
   ```bash
   cd src/dataIngestion
   pip install -r requirements.txt
   ```

2. **Set up environment (optional for OpenAI tests):**
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   ```

### Running All Tests

```bash
# Run with mock tests only (no API key required)
python tests/run_tests.py

# Run with OpenAI evaluation tests (requires API key)
python tests/run_tests.py --openai

# Run with verbose output
python tests/run_tests.py --verbose
```

### Running Individual Test Files

```bash
# Run main test suite
python tests/test_ai_categorization.py

# Run with unittest directly
python -m unittest tests.test_ai_categorization -v
```

### Running Specific Test Classes

```bash
# Run only mock tests
python -m unittest tests.test_ai_categorization.TestAICategorization -v

# Run only OpenAI evaluation tests
python -m unittest tests.test_ai_categorization.TestOpenAIEvaluation -v
```

## Test Data

The test suite includes sample content for each supported framework:

- **Semantic Kernel** - Basic tutorial content
- **ML.NET** - Machine learning tutorial
- **Semantic Kernel Agents** - Agent framework content
- **Microsoft.Extensions.AI** - AI extensions content
- **AutoGen** - AutoGen framework content
- **OpenAI SDK** - OpenAI SDK content

## Expected Results

### Framework Categories
All tests should validate that these 7 framework categories are available:
- Microsoft.Extensions.AI
- ML.NET
- AutoGen
- Semantic Kernel
- Semantic Kernel Agents
- Semantic Kernel Process Framework
- OpenAI SDK

### Semantic Kernel Family Logic
Content mentioning Semantic Kernel sub-frameworks should automatically include both:
- The specific framework tag (e.g., "Semantic Kernel Agents")
- The parent framework tag ("Semantic Kernel")

### Validation Rules
- Content should be truncated to 2000 characters for API calls
- AI responses should be comma-separated framework names
- Invalid tags should be filtered out
- Empty content should return empty results
- API errors should be handled gracefully

## Test Output

### Successful Test Run
```
============================================================
RAG Data Ingestion Pipeline - Test Suite
============================================================
Running tests with mock OpenAI responses only
Set OPENAI_API_KEY environment variable to enable real API tests
test_framework_categories_available (__main__.TestAICategorization) ... ok
test_semantic_kernel_categorization (__main__.TestAICategorization) ... ok
test_semantic_kernel_agents_categorization (__main__.TestAICategorization) ... ok
test_ml_net_categorization (__main__.TestAICategorization) ... ok
test_tag_validation (__main__.TestAICategorization) ... ok
test_openai_error_handling (__main__.TestAICategorization) ... ok
test_empty_content_handling (__main__.TestAICategorization) ... ok

----------------------------------------------------------------------
Ran 7 tests in 0.123s

OK
============================================================
✅ All tests passed!
```

### With OpenAI Evaluation
```
============================================================
RAG Data Ingestion Pipeline - Test Suite
============================================================
Running tests with OpenAI evaluation enabled
test_framework_categories_available (__main__.TestAICategorization) ... ok
test_semantic_kernel_categorization (__main__.TestAICategorization) ... ok
test_semantic_kernel_agents_categorization (__main__.TestAICategorization) ... ok
test_ml_net_categorization (__main__.TestAICategorization) ... ok
test_tag_validation (__main__.TestAICategorization) ... ok
test_openai_error_handling (__main__.TestAICategorization) ... ok
test_empty_content_handling (__main__.TestAICategorization) ... ok
test_real_semantic_kernel_categorization (__main__.TestOpenAIEvaluation) ... ok
Real API result for Semantic Kernel: ['Semantic Kernel']
test_real_ml_net_categorization (__main__.TestOpenAIEvaluation) ... ok
Real API result for ML.NET: ['ML.NET']
test_real_semantic_kernel_agents_categorization (__main__.TestOpenAIEvaluation) ... ok
Real API result for Semantic Kernel Agents: ['Semantic Kernel Agents', 'Semantic Kernel']

----------------------------------------------------------------------
Ran 10 tests in 5.234s

OK
============================================================
✅ All tests passed!
```

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure you're running from the `src/dataIngestion` directory
   - Check that all dependencies are installed

2. **OpenAI API Errors**
   - Verify your API key is valid and has sufficient credits
   - Check network connectivity
   - Ensure the OpenAI package is installed

3. **Test Failures**
   - Review the test output for specific failure details
   - Check that the AI categorization logic matches expected behavior
   - Verify framework categories are correctly defined

### Debug Mode

Enable debug logging for more detailed output:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

When adding new tests:

1. **Follow the existing pattern** - Use the same structure as existing tests
2. **Include both mock and real tests** - Mock tests for reliability, real tests for validation
3. **Add test data** - Include sample content in `test_config.py`
4. **Update documentation** - Keep this README current with new test descriptions

## Test Coverage

The test suite covers:

- ✅ Framework category validation
- ✅ AI categorization logic
- ✅ Semantic Kernel family logic
- ✅ Error handling
- ✅ Edge cases
- ✅ Real API integration (with API key)
- ✅ Tag validation
- ✅ Content processing

This provides comprehensive validation of the core AI categorization functionality. 