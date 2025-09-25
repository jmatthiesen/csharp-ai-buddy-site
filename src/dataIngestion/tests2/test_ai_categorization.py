#!/usr/bin/env python3
"""
Tests for AI categorization logic using OpenAI evaluations.
Simple validation tests to ensure core functionality works.
"""

import os
import sys
import unittest
from unittest.mock import Mock, patch
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotnet_sdk_tags import categorize_with_ai, validate_framework_tags


class TestAICategorization(unittest.TestCase):
    """Test cases for AI-powered framework categorization."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock OpenAI client for testing
        self.mock_openai_client = Mock()
        
        # Test content samples
        self.test_content = {
            "semantic_kernel": """
            # Getting Started with Semantic Kernel
            
            Semantic Kernel is Microsoft's AI orchestration library for .NET.
            Learn how to build AI applications with Semantic Kernel.
            
            ```csharp
            var kernel = Kernel.CreateBuilder()
                .AddOpenAIChatCompletion("gpt-4", "your-api-key")
                .Build();
            ```
            """,
            
            "ml_net": """
            # ML.NET Tutorial
            
            ML.NET is Microsoft's machine learning framework for .NET developers.
            Build custom ML models with C# and F#.
            
            ```csharp
            var mlContext = new MLContext();
            var dataView = mlContext.Data.LoadFromTextFile<SentimentData>("data.csv");
            ```
            """,
            
            "semantic_kernel_agents": """
            # Semantic Kernel Agents
            
            Build intelligent agents with Semantic Kernel Agents framework.
            Create multi-agent conversations and workflows.
            
            ```csharp
            var agent = new ChatCompletionAgent(kernel, "You are a helpful assistant.");
            var result = await agent.InvokeAsync("What is the weather?");
            ```
            """
        }
    
    def test_semantic_kernel_categorization(self):
        """Test AI categorization for Semantic Kernel content."""
        # Mock OpenAI response for Semantic Kernel content
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Semantic Kernel"
        
        self.mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Test categorization
        result = categorize_with_ai(self.test_content["semantic_kernel"], self.mock_openai_client)
        
        # Verify OpenAI was called
        self.mock_openai_client.chat.completions.create.assert_called_once()
        
        # Verify result contains expected framework
        self.assertIn("Semantic Kernel", result, "Semantic Kernel should be detected")
        self.assertTrue(len(result) > 0, "Should return at least one framework")
    
    def test_semantic_kernel_agents_categorization(self):
        """Test AI categorization for Semantic Kernel Agents content (should include both tags)."""
        # Mock OpenAI response for Semantic Kernel Agents content
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Semantic Kernel Agents, Semantic Kernel"
        
        self.mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Test categorization
        result = categorize_with_ai(self.test_content["semantic_kernel_agents"], self.mock_openai_client)
        
        # Verify OpenAI was called
        self.mock_openai_client.chat.completions.create.assert_called_once()
        
        # Verify both tags are present
        self.assertIn("Semantic Kernel Agents", result, "Semantic Kernel Agents should be detected")
        self.assertIn("Semantic Kernel", result, "Parent Semantic Kernel tag should be included")
    
    def test_ml_net_categorization(self):
        """Test AI categorization for ML.NET content."""
        # Mock OpenAI response for ML.NET content
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "ML.NET"
        
        self.mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Test categorization
        result = categorize_with_ai(self.test_content["ml_net"], self.mock_openai_client)
        
        # Verify OpenAI was called
        self.mock_openai_client.chat.completions.create.assert_called_once()
        
        # Verify result contains expected framework
        self.assertIn("ML.NET", result, "ML.NET should be detected")
        self.assertTrue(len(result) > 0, "Should return at least one framework")
    
    def test_tag_validation(self):
        """Test framework tag validation."""
        valid_tags = ["Semantic Kernel", "ML.NET", "Microsoft.Extensions.AI"]
        invalid_tags = ["Invalid Tag", "Unknown Framework", "Random Tag"]
        mixed_tags = valid_tags + invalid_tags
        
        # Test valid tags
        valid_result, invalid_result = validate_framework_tags(valid_tags)
        self.assertEqual(valid_result, valid_tags, "All valid tags should be accepted")
        self.assertEqual(invalid_result, [], "No invalid tags should be found")
        
        # Test invalid tags
        valid_result, invalid_result = validate_framework_tags(invalid_tags)
        self.assertEqual(valid_result, [], "No valid tags should be found")
        self.assertEqual(invalid_result, invalid_tags, "All invalid tags should be rejected")
        
        # Test mixed tags
        valid_result, invalid_result = validate_framework_tags(mixed_tags)
        self.assertEqual(valid_result, valid_tags, "Valid tags should be separated")
        self.assertEqual(invalid_result, invalid_tags, "Invalid tags should be separated")
    
    def test_openai_error_handling(self):
        """Test error handling when OpenAI API fails."""
        # Mock OpenAI to raise an exception
        self.mock_openai_client.chat.completions.create.side_effect = Exception("API Error")
        
        # Test categorization should handle error gracefully
        result = categorize_with_ai(self.test_content["semantic_kernel"], self.mock_openai_client)
        
        # Should return empty list on error
        self.assertEqual(result, [], "Should return empty list when OpenAI fails")
    
    def test_empty_content_handling(self):
        """Test handling of empty or minimal content."""
        # Mock OpenAI response for empty content
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "None"
        
        self.mock_openai_client.chat.completions.create.return_value = mock_response
        
        # Test with empty content
        result = categorize_with_ai("", self.mock_openai_client)
        self.assertEqual(result, [], "Empty content should return empty list")
        
        # Test with minimal content
        result = categorize_with_ai("Hello world", self.mock_openai_client)
        self.assertEqual(result, [], "Minimal content should return empty list")


class TestOpenAIEvaluation(unittest.TestCase):
    """Test cases using actual OpenAI API for evaluation (requires API key)."""
    
    def setUp(self):
        """Set up OpenAI client for evaluation tests."""
        try:
            from openai import OpenAI
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                self.skipTest("OPENAI_API_KEY environment variable not set")
            
            self.client = OpenAI(api_key=api_key)
            self.evaluation_enabled = True
        except ImportError:
            self.skipTest("OpenAI client not available")
        except Exception as e:
            self.skipTest(f"OpenAI client setup failed: {e}")
    
    def test_real_semantic_kernel_categorization(self):
        """Test real OpenAI categorization for Semantic Kernel content."""
        if not self.evaluation_enabled:
            self.skipTest("OpenAI evaluation not enabled")
        
        content = """
        # Semantic Kernel Tutorial
        
        Learn how to use Semantic Kernel for building AI applications in .NET.
        Semantic Kernel provides a powerful framework for AI orchestration.
        
        ```csharp
        var kernel = Kernel.CreateBuilder()
            .AddOpenAIChatCompletion("gpt-4", "your-api-key")
            .Build();
        ```
        """
        
        result = categorize_with_ai(content, self.client)
        
        # Should detect Semantic Kernel
        self.assertIn("Semantic Kernel", result, "Real API should detect Semantic Kernel")
        print(f"Real API result for Semantic Kernel: {result}")
    
    def test_real_ml_net_categorization(self):
        """Test real OpenAI categorization for ML.NET content."""
        if not self.evaluation_enabled:
            self.skipTest("OpenAI evaluation not enabled")
        
        content = """
        # ML.NET Machine Learning
        
        ML.NET is Microsoft's machine learning framework for .NET developers.
        Build custom ML models with C# and F# using ML.NET.
        
        ```csharp
        var mlContext = new MLContext();
        var dataView = mlContext.Data.LoadFromTextFile<SentimentData>("data.csv");
        ```
        """
        
        result = categorize_with_ai(content, self.client)
        
        # Should detect ML.NET
        self.assertIn("ML.NET", result, "Real API should detect ML.NET")
        print(f"Real API result for ML.NET: {result}")
    
    def test_real_semantic_kernel_agents_categorization(self):
        """Test real OpenAI categorization for Semantic Kernel Agents content."""
        if not self.evaluation_enabled:
            self.skipTest("OpenAI evaluation not enabled")
        
        content = """
        # Semantic Kernel Agents
        
        Build intelligent agents with Semantic Kernel Agents framework.
        Create multi-agent conversations and workflows using Semantic Kernel Agents.
        
        ```csharp
        var agent = new ChatCompletionAgent(kernel, "You are a helpful assistant.");
        var result = await agent.InvokeAsync("What is the weather?");
        ```
        """
        
        result = categorize_with_ai(content, self.client)
        
        # Should detect both Semantic Kernel Agents and Semantic Kernel
        self.assertIn("Semantic Kernel Agents", result, "Real API should detect Semantic Kernel Agents")
        self.assertIn("Semantic Kernel", result, "Real API should include parent Semantic Kernel tag")
        print(f"Real API result for Semantic Kernel Agents: {result}")

    def test_two_tags(self):
        """Test real OpenAI categorization for Semantic Kernel Agents content."""
        if not self.evaluation_enabled:
            self.skipTest("OpenAI evaluation not enabled")
        
        content = """
        # Semantic Kernel and Microsoft.Extensions.AI
        
        Build intelligent agents with Semantic Kernel .
        Built using primitives from Microsoft.Extensions.AI.
        """
        
        result = categorize_with_ai(content, self.client)
        
        # Should detect both Semantic Kernel  and Microsoft.Extensions.AI
        self.assertIn("Semantic Kernel", result, "Real API should detect Semantic Kernel")
        self.assertIn("Microsoft.Extensions.AI", result, "Real API should detect Microsoft.Extensions.AI")
        print(f"Real API result for Semantic Kernel and Microsoft.Extensions.AI: {result}")

def run_tests():
    """Run all tests with optional OpenAI evaluation."""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add mock tests (always run)
    test_suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(TestAICategorization))
    
    # Add OpenAI evaluation tests (if API key available)
    if os.getenv("OPENAI_API_KEY"):
        test_suite.addTest(unittest.defaultTestLoader.loadTestsFromTestCase(TestOpenAIEvaluation))
        print("Running tests with OpenAI evaluation enabled")
    else:
        print("Running tests with mock OpenAI responses only")
        print("Set OPENAI_API_KEY environment variable to enable real API tests")
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 