#!/usr/bin/env python3
"""
Integration test for the AI evaluation framework.

This test verifies that the evaluation framework works correctly without making
actual OpenAI API calls (uses mocked responses for testing).
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evals.prompt_evaluator import PromptEvaluator, EvaluationResult, EvaluationMetrics


class TestEvaluationFramework(unittest.TestCase):
    """Test cases for the evaluation framework."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock OpenAI client to avoid API calls during testing
        self.mock_client = Mock()
        
        # Create evaluator with mocked client
        with patch('evals.prompt_evaluator.OpenAI', return_value=self.mock_client):
            self.evaluator = PromptEvaluator(api_key="test-key")
            self.evaluator.client = self.mock_client
    
    def test_load_test_cases(self):
        """Test loading test cases from JSON file."""
        # Create a temporary test case file
        test_cases = [
            {
                "id": "test_1",
                "input": "How do I use Semantic Kernel?",
                "expected": "Create a kernel with Kernel.CreateBuilder()",
                "criteria": "accuracy"
            }
        ]
        
        # Mock file reading
        with patch('builtins.open', mock_open_with_json(test_cases)):
            loaded_cases = self.evaluator.load_test_cases("test_file.json")
        
        self.assertEqual(len(loaded_cases), 1)
        self.assertEqual(loaded_cases[0]["id"], "test_1")
        self.assertEqual(loaded_cases[0]["input"], "How do I use Semantic Kernel?")
    
    def test_evaluate_prompt_accuracy(self):
        """Test prompt accuracy evaluation with mocked OpenAI responses."""
        # Mock OpenAI responses
        mock_completion_response = Mock()
        mock_completion_response.choices = [Mock()]
        mock_completion_response.choices[0].message.content = "Here's how to use Semantic Kernel..."
        
        mock_evaluation_response = Mock()
        mock_evaluation_response.choices = [Mock()]
        mock_evaluation_response.choices[0].message.content = "0.85"
        
        self.mock_client.chat.completions.create.side_effect = [
            mock_completion_response,
            mock_evaluation_response
        ]
        
        # Test evaluation
        score = self.evaluator.evaluate_prompt_accuracy(
            "You are a C# AI assistant",
            "How do I use Semantic Kernel?",
            "Expected response about kernel creation"
        )
        
        self.assertEqual(score, 0.85)
        self.assertEqual(self.mock_client.chat.completions.create.call_count, 2)
    
    def test_evaluate_code_correctness(self):
        """Test code correctness evaluation."""
        # Mock OpenAI response for code evaluation
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "0.92"
        
        self.mock_client.chat.completions.create.return_value = mock_response
        
        # Test code evaluation
        code = """
        var kernel = Kernel.CreateBuilder()
            .AddOpenAIChatCompletion("gpt-4", apiKey)
            .Build();
        """
        
        score = self.evaluator.evaluate_code_correctness(code, "csharp")
        
        self.assertEqual(score, 0.92)
        self.mock_client.chat.completions.create.assert_called_once()
    
    def test_run_evaluation_suite(self):
        """Test running a complete evaluation suite."""
        # Mock OpenAI responses
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Semantic Kernel is Microsoft's AI orchestration library..."
        
        mock_eval_response = Mock()
        mock_eval_response.choices = [Mock()]
        mock_eval_response.choices[0].message.content = "0.78"
        
        self.mock_client.chat.completions.create.side_effect = [
            mock_response,
            mock_eval_response
        ]
        
        # Test cases
        test_cases = [
            {
                "id": "semantic_kernel_test",
                "input": "How do I create a Semantic Kernel application?",
                "expected": "Use Kernel.CreateBuilder()",
                "criteria": "accuracy",
                "metadata": {"category": "semantic_kernel"}
            }
        ]
        
        # Run evaluation suite
        results = self.evaluator.run_evaluation_suite(
            "test_prompt",
            "You are a C# AI assistant",
            test_cases
        )
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].prompt_id, "test_prompt")
        self.assertEqual(results[0].test_case_id, "semantic_kernel_test")
        self.assertEqual(results[0].score, 0.78)
    
    def test_calculate_metrics(self):
        """Test metrics calculation."""
        # Create sample evaluation results
        results = [
            EvaluationResult(
                prompt_id="test",
                test_case_id="test_1",
                input_query="query 1",
                expected_response="expected 1",
                actual_response="actual 1",
                score=0.85,
                evaluation_criteria="accuracy",
                timestamp=datetime.now(),
                metadata={}
            ),
            EvaluationResult(
                prompt_id="test",
                test_case_id="test_2",
                input_query="query 2",
                expected_response="expected 2",
                actual_response="actual 2",
                score=0.65,
                evaluation_criteria="accuracy",
                timestamp=datetime.now(),
                metadata={}
            ),
            EvaluationResult(
                prompt_id="test",
                test_case_id="test_3",
                input_query="query 3",
                expected_response="expected 3",
                actual_response="actual 3",
                score=0.92,
                evaluation_criteria="accuracy",
                timestamp=datetime.now(),
                metadata={}
            )
        ]
        
        # Calculate metrics
        metrics = self.evaluator.calculate_metrics(results)
        
        self.assertEqual(metrics.total_tests, 3)
        self.assertEqual(metrics.passed_tests, 2)  # scores >= 0.7
        self.assertEqual(metrics.failed_tests, 1)
        self.assertAlmostEqual(metrics.average_score, 0.8067, places=3)
        
        # Check score distribution
        self.assertEqual(metrics.score_distribution["0.6-0.8"], 1)
        self.assertEqual(metrics.score_distribution["0.8-1.0"], 2)
    
    def test_generate_report(self):
        """Test report generation."""
        # Create sample results and metrics
        results = [
            EvaluationResult(
                prompt_id="test",
                test_case_id="test_1",
                input_query="Short query",
                expected_response="expected",
                actual_response="actual",
                score=0.85,
                evaluation_criteria="accuracy",
                timestamp=datetime.now(),
                metadata={}
            )
        ]
        
        metrics = self.evaluator.calculate_metrics(results)
        report = self.evaluator.generate_report(results, metrics)
        
        self.assertIn("AI Prompt Evaluation Report", report)
        self.assertIn("Total Tests**: 1", report)
        self.assertIn("Average Score**: 0.850", report)
        self.assertIn("test_1", report)
    
    def test_error_handling(self):
        """Test error handling in evaluation methods."""
        # Mock OpenAI to raise an exception
        self.mock_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Test that errors are handled gracefully
        score = self.evaluator.evaluate_prompt_accuracy(
            "system prompt",
            "user query"
        )
        
        self.assertEqual(score, 0.0)  # Should return 0.0 on error
    
    def test_save_results(self):
        """Test saving evaluation results."""
        # Create sample results
        results = [
            EvaluationResult(
                prompt_id="test",
                test_case_id="test_1",
                input_query="query",
                expected_response="expected",
                actual_response="actual",
                score=0.85,
                evaluation_criteria="accuracy",
                timestamp=datetime.now(),
                metadata={}
            )
        ]
        
        # Mock file operations
        with patch('builtins.open', mock_open_write()) as mock_file:
            with patch('pathlib.Path.mkdir'):
                filepath = self.evaluator.save_results(results, "test_results.json")
        
        self.assertTrue(filepath.endswith("test_results.json"))
        mock_file.assert_called_once()


def mock_open_with_json(json_data):
    """Helper function to mock file opening with JSON data."""
    from unittest.mock import mock_open
    return mock_open(read_data=json.dumps(json_data))


def mock_open_write():
    """Helper function to mock file writing."""
    from unittest.mock import mock_open
    return mock_open()


def run_integration_tests():
    """Run all integration tests."""
    # Create test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestEvaluationFramework)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    if result.wasSuccessful():
        print("\n✅ All integration tests passed!")
        print("🎉 The AI evaluation framework is ready to use!")
        print("\nNext steps:")
        print("1. Set your OPENAI_API_KEY environment variable")
        print("2. Run: python evals/run_evaluations.py --component all")
        print("3. Check the results in evals/results/")
    else:
        print("\n❌ Some integration tests failed!")
        print("Please review the test output above and fix any issues.")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)