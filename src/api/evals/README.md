# AI Prompt Evaluation Framework

A comprehensive evaluation system for testing AI prompts used in the C# AI Buddy application

## Overview

This framework provides automated evaluation capabilities for:

- **Main AI Assistant Prompt**: Tests the core system prompt that guides the C# AI Buddy's responses
- **AI Categorization Prompt**: Evaluates the accuracy of AI framework categorization in the data ingestion pipeline
- **Code Generation Quality**: Assesses the correctness and quality of generated C# code examples
- **Response Accuracy**: Measures how well responses match expected outcomes and user intent

## Features

- 🔍 **Comprehensive Testing**: Evaluates both conversational AI and categorization AI components
- 📊 **Detailed Metrics**: Provides accuracy scores, pass/fail rates, and performance distributions
- 📈 **Automated Reporting**: Generates markdown reports with actionable insights
- 🚀 **CI/CD Integration**: Ready for integration into continuous integration pipelines
- 📝 **Extensible Test Cases**: Easy to add new test scenarios and evaluation criteria

## Quick Start

### Prerequisites

1. Python 3.8+ installed
2. OpenAI API key with access to GPT-4
3. All dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

### Environment Setup

1. Set your OpenAI API key:
   ```bash
   export OPENAI_API_KEY="your-api-key-here"
   ```

2. Verify the framework works:
   ```bash
   cd src/api
   python evals/test_evaluation_framework.py
   ```

### Running Evaluations

#### Evaluate All Components
```bash
python evals/run_evaluations.py --component all
```

#### Evaluate Specific Components
```bash
# Main AI assistant only
python evals/run_evaluations.py --component main

# Categorization system only
python evals/run_evaluations.py --component categorization
```

### Viewing Results

Results are saved in `evals/results/` with timestamps:

- `comprehensive_report_YYYYMMDD_HHMMSS.md` - Human-readable report
- `main_assistant_results_YYYYMMDD_HHMMSS.json` - Detailed JSON results
- `categorization_results_YYYYMMDD_HHMMSS.json` - Categorization test results

## Test Cases

### Main Assistant Tests (`test_cases/csharp_ai_buddy_tests.json`)

Tests for the main AI assistant covering:

- **Semantic Kernel**: Basic setup, agents, advanced concepts
- **ML.NET**: Model training, sentiment analysis, data processing
- **Azure AI Services**: Integration patterns, authentication
- **Code Translation**: Python to C# conversions
- **Security**: Best practices, API key management
- **Error Handling**: Exception patterns, retry logic
- **Performance**: Async programming, memory optimization

### Categorization Tests (`test_cases/categorization_tests.json`)

Tests for AI framework categorization including:

- **Single Framework Detection**: Semantic Kernel, ML.NET, Azure AI
- **Multiple Framework Detection**: Complex content with multiple frameworks
- **Edge Cases**: No AI frameworks, ambiguous content
- **Accuracy Testing**: Precise framework identification

## Evaluation Criteria

### Scoring System

- **1.0 (Excellent)**: Perfect response, fully addresses query
- **0.8-0.9 (Good)**: High quality with minor issues
- **0.6-0.7 (Adequate)**: Functional but with notable gaps
- **0.4-0.5 (Poor)**: Significant issues or inaccuracies
- **0.0-0.3 (Very Poor)**: Incorrect or unhelpful response

### Pass Threshold

- **Default**: 0.7 (70% quality threshold)
- **Configurable**: Adjust in `config.yaml`

## Framework Architecture

```
evals/
├── prompt_evaluator.py      # Core evaluation engine
├── run_evaluations.py       # Main evaluation runner
├── config.yaml             # Configuration settings
├── test_cases/             # Test case definitions
│   ├── csharp_ai_buddy_tests.json
│   └── categorization_tests.json
├── results/                # Generated reports and results
└── README.md              # This documentation
```

### Key Components

- **`PromptEvaluator`**: Core class handling OpenAI API interactions and scoring
- **`ComprehensiveEvaluationRunner`**: Orchestrates evaluation across all components
- **`EvaluationResult`**: Data structure for individual test results
- **`EvaluationMetrics`**: Aggregated statistics and performance metrics

## Adding New Test Cases

### Main Assistant Tests

Add to `test_cases/csharp_ai_buddy_tests.json`:

```json
{
  "id": "new_test_case",
  "input": "User query to test",
  "expected": "Expected response pattern",
  "criteria": "accuracy",
  "metadata": {
    "category": "test_category",
    "difficulty": "beginner|intermediate|advanced",
    "tags": ["tag1", "tag2"]
  }
}
```

### Categorization Tests

Add to `test_cases/categorization_tests.json`:

```json
{
  "id": "framework_detection_test",
  "input": "Content to categorize with code examples",
  "expected": "Framework Name, Another Framework",
  "criteria": "categorization_accuracy",
  "metadata": {
    "expected_tags": ["Framework Name", "Another Framework"]
  }
}
```

## Configuration

Edit `config.yaml` to customize:

```yaml
evaluation:
  model: "gpt-4"              # Evaluation model
  temperature: 0.1            # Response consistency
  pass_threshold: 0.7         # Quality threshold

automation:
  fail_build_on_threshold: 0.6  # CI/CD failure threshold
  run_on_prompt_changes: true   # Auto-run on changes
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: AI Prompt Evaluation

on:
  pull_request:
    paths:
      - 'src/api/main.py'
      - 'src/dataIngestion/dotnet_sdk_tags.py'

jobs:
  evaluate-prompts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install -r src/api/requirements.txt
      - name: Run evaluations
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          cd src/api
          python evals/run_evaluations.py --component all
      - name: Upload results
        uses: actions/upload-artifact@v2
        with:
          name: evaluation-results
          path: src/api/evals/results/
```

## Best Practices

### Test Case Design

1. **Diverse Scenarios**: Cover beginner to advanced use cases
2. **Real-World Queries**: Use actual user questions when possible
3. **Edge Cases**: Include boundary conditions and error scenarios
4. **Clear Expectations**: Define specific, measurable expected outcomes

### Prompt Engineering

1. **Monitor Trends**: Track evaluation scores over time
2. **Iterative Improvement**: Use failed tests to guide prompt improvements
3. **A/B Testing**: Compare different prompt versions
4. **Regular Updates**: Keep test cases current with new features

### Performance Monitoring

1. **Baseline Establishment**: Set initial performance benchmarks
2. **Regression Detection**: Alert on score decreases
3. **Continuous Evaluation**: Run tests regularly, not just on changes
4. **Threshold Management**: Adjust pass thresholds based on requirements

## Troubleshooting

### Common Issues

#### OpenAI API Errors
```bash
Error: OpenAI API key is required
```
**Solution**: Set the `OPENAI_API_KEY` environment variable

#### Import Errors
```bash
ModuleNotFoundError: No module named 'evals.prompt_evaluator'
```
**Solution**: Run from the `src/api` directory

#### Low Evaluation Scores
**Analysis Steps**:
1. Review failed test cases in the detailed report
2. Check if prompts need more specific instructions
3. Verify test case expectations are realistic
4. Consider if additional context or examples are needed

#### Rate Limiting
```bash
Error: Rate limit exceeded
```
**Solution**: Add delays between API calls or use a higher-tier API plan

## Contributing

### Adding New Evaluation Criteria

1. Extend the `PromptEvaluator` class with new evaluation methods
2. Add corresponding test cases
3. Update the configuration schema
4. Document the new criteria in this README

### Improving Test Coverage

1. Analyze current test gaps using the evaluation reports
2. Add test cases for uncovered scenarios
3. Include both positive and negative test cases
4. Test edge cases and error conditions

## Advanced Usage

### Custom Evaluation Models

You can use different models for different evaluation types:

```python
evaluator = PromptEvaluator()
# Use GPT-4 for complex reasoning tasks
evaluator.model = "gpt-4"
# Use GPT-3.5 for simple categorization
categorization_model = "gpt-3.5-turbo"
```

### Batch Evaluation

For large test suites, consider batch processing:

```python
results = []
for batch in test_case_batches:
    batch_results = evaluator.run_evaluation_suite(
        prompt_id, system_prompt, batch
    )
    results.extend(batch_results)
    time.sleep(1)  # Rate limiting
```

### Custom Scoring Functions

Implement domain-specific scoring:

```python
def custom_code_quality_score(code, expected_patterns):
    score = 0.0
    # Custom logic for code quality assessment
    # Check syntax, best practices, security, etc.
    return score
```

## Support

For questions or issues:

1. Check the troubleshooting section above
2. Review the test output for specific error messages
3. Ensure all dependencies are correctly installed
4. Verify your OpenAI API key has sufficient permissions

## Future Enhancements

- [ ] Integration with additional LLM providers
- [ ] Visual evaluation dashboard
- [ ] A/B testing framework for prompt variations
- [ ] Automated prompt optimization suggestions
- [ ] Integration with prompt versioning systems
- [ ] Performance benchmarking against industry standards