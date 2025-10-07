#!/usr/bin/env python3
"""
AI Prompt Evaluation Framework using OpenAI Evals

This module provides comprehensive evaluation capabilities for AI prompts used in the C# AI Buddy application.
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import logging
from pathlib import Path

from openai import OpenAI
import pandas as pd

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Represents the result of a single evaluation."""
    prompt_id: str
    test_case_id: str
    input_query: str
    expected_response: Optional[str]
    actual_response: str
    score: float
    evaluation_criteria: str
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class EvaluationMetrics:
    """Aggregated metrics for a set of evaluations."""
    total_tests: int
    passed_tests: int
    failed_tests: int
    average_score: float
    score_distribution: Dict[str, int]
    timestamp: datetime


class PromptEvaluator:
    """
    Main evaluation class that integrates with OpenAI Evals to test AI prompts.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the PromptEvaluator.
        
        Args:
            api_key: OpenAI API key. If None, will look for OPENAI_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.evaluation_results: List[EvaluationResult] = []
        
        # Ensure results directory exists
        self.results_dir = Path("evals/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
    
    def load_test_cases(self, test_file_path: str) -> List[Dict[str, Any]]:
        """
        Load test cases from a JSON file.
        
        Args:
            test_file_path: Path to the JSON file containing test cases.
            
        Returns:
            List of test case dictionaries.
        """
        try:
            with open(test_file_path, 'r') as f:
                test_cases = json.load(f)
            logger.info(f"Loaded {len(test_cases)} test cases from {test_file_path}")
            return test_cases
        except Exception as e:
            logger.error(f"Error loading test cases from {test_file_path}: {e}")
            return []
    
    def evaluate_prompt_accuracy(self, prompt: str, user_query: str, expected_response: Optional[str] = None) -> float:
        """
        Evaluate the accuracy of a prompt's response using GPT-4 as a judge.
        
        Args:
            prompt: The system prompt to evaluate.
            user_query: The user's input query.
            expected_response: Optional expected response for comparison.
            
        Returns:
            Accuracy score between 0.0 and 1.0.
        """
        try:
            # Generate response using the Responses API
            response = self.client.responses.create(
                model="gpt-4o",
                instructions=prompt,
                input=user_query,
                temperature=0.1
            )
            
            actual_response = response.output_text
            
            # Use GPT-4 as a judge to evaluate the response
            evaluation_prompt = f"""
            You are an expert evaluator of AI responses for C# and .NET development questions.
            
            Please evaluate the following response based on these criteria:
            1. Technical accuracy of C#/.NET information
            2. Code quality and best practices
            3. Completeness of the answer
            4. Clarity and helpfulness
            5. Security considerations (if applicable)
            
            User Query: {user_query}
            
            AI Response: {actual_response}
            
            {f"Expected Response (for reference): {expected_response}" if expected_response else ""}
            
            Provide a score from 0.0 to 1.0 where:
            - 1.0 = Excellent response that fully addresses the query with accurate, complete, and helpful information
            - 0.8-0.9 = Good response with minor issues or missing details
            - 0.6-0.7 = Adequate response but with notable gaps or inaccuracies
            - 0.4-0.5 = Poor response with significant issues
            - 0.0-0.3 = Very poor or incorrect response
            
            Respond with only the numerical score (e.g., 0.85).
            """
            
            evaluation_response = self.client.responses.create(
                model="gpt-4o",
                instructions="You are an expert evaluator. Respond with only a numerical score between 0.0 and 1.0.",
                input=evaluation_prompt,
                temperature=0.1
            )
            
            score_text = evaluation_response.output_text.strip()
            score = float(score_text)
            
            logger.info(f"Evaluated response with score: {score}")
            return score
            
        except Exception as e:
            logger.error(f"Error evaluating prompt accuracy: {e}")
            return 0.0
    
    def evaluate_code_correctness(self, generated_code: str, language: str = "csharp") -> float:
        """
        Evaluate the correctness of generated code.
        
        Args:
            generated_code: The code snippet to evaluate.
            language: Programming language (default: csharp).
            
        Returns:
            Correctness score between 0.0 and 1.0.
        """
        evaluation_prompt = f"""
        You are an expert code reviewer specializing in {language}.
        
        Please evaluate the following code snippet for:
        1. Syntax correctness
        2. Compilation viability
        3. Best practices adherence
        4. Security considerations
        5. Performance implications
        
        Code to evaluate:
        ```{language}
        {generated_code}
        ```
        
        Provide a score from 0.0 to 1.0 where:
        - 1.0 = Perfect code with no issues
        - 0.8-0.9 = Good code with minor style or performance improvements possible
        - 0.6-0.7 = Functional code but with notable issues
        - 0.4-0.5 = Code with significant problems that may prevent compilation
        - 0.0-0.3 = Severely flawed or non-functional code
        
        Respond with only the numerical score (e.g., 0.85).
        """
        
        try:
            response = self.client.responses.create(
                model="gpt-4o",
                instructions="You are an expert code reviewer. Respond with only a numerical score between 0.0 and 1.0.",
                input=evaluation_prompt,
                temperature=0.1
            )
            
            score_text = response.output_text.strip()
            score = float(score_text)
            
            logger.info(f"Code correctness score: {score}")
            return score
            
        except Exception as e:
            logger.error(f"Error evaluating code correctness: {e}")
            return 0.0
    
    def run_evaluation_suite(self, prompt_id: str, system_prompt: str, test_cases: List[Dict[str, Any]]) -> List[EvaluationResult]:
        """
        Run a complete evaluation suite for a given prompt.
        
        Args:
            prompt_id: Unique identifier for the prompt being tested.
            system_prompt: The system prompt to evaluate.
            test_cases: List of test case dictionaries.
            
        Returns:
            List of EvaluationResult objects.
        """
        results = []
        
        for i, test_case in enumerate(test_cases):
            try:
                test_case_id = test_case.get('id', f"test_{i}")
                user_query = test_case.get('input', '')
                expected_response = test_case.get('expected', None)
                evaluation_criteria = test_case.get('criteria', 'accuracy')
                
                logger.info(f"Running evaluation for test case: {test_case_id}")
                
                # Generate actual response using Responses API
                response = self.client.responses.create(
                    model="gpt-4o",
                    instructions=system_prompt,
                    input=user_query,
                    temperature=0.1
                )
                
                actual_response = response.output_text
                
                # Evaluate based on criteria
                if evaluation_criteria == 'code_correctness':
                    score = self.evaluate_code_correctness(actual_response)
                else:
                    score = self.evaluate_prompt_accuracy(system_prompt, user_query, expected_response)
                
                # Create evaluation result
                result = EvaluationResult(
                    prompt_id=prompt_id,
                    test_case_id=test_case_id,
                    input_query=user_query,
                    expected_response=expected_response,
                    actual_response=actual_response,
                    score=score,
                    evaluation_criteria=evaluation_criteria,
                    timestamp=datetime.now(),
                    metadata=test_case.get('metadata', {})
                )
                
                results.append(result)
                self.evaluation_results.append(result)
                
            except Exception as e:
                logger.error(f"Error evaluating test case {test_case_id}: {e}")
                continue
        
        return results
    
    def calculate_metrics(self, results: List[EvaluationResult], pass_threshold: float = 0.7) -> EvaluationMetrics:
        """
        Calculate aggregated metrics from evaluation results.
        
        Args:
            results: List of EvaluationResult objects.
            pass_threshold: Score threshold for considering a test as passed.
            
        Returns:
            EvaluationMetrics object with aggregated statistics.
        """
        if not results:
            return EvaluationMetrics(0, 0, 0, 0.0, {}, datetime.now())
        
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r.score >= pass_threshold)
        failed_tests = total_tests - passed_tests
        average_score = sum(r.score for r in results) / total_tests
        
        # Score distribution
        score_ranges = {
            "0.0-0.2": 0, "0.2-0.4": 0, "0.4-0.6": 0,
            "0.6-0.8": 0, "0.8-1.0": 0
        }
        
        for result in results:
            if result.score < 0.2:
                score_ranges["0.0-0.2"] += 1
            elif result.score < 0.4:
                score_ranges["0.2-0.4"] += 1
            elif result.score < 0.6:
                score_ranges["0.4-0.6"] += 1
            elif result.score < 0.8:
                score_ranges["0.6-0.8"] += 1
            else:
                score_ranges["0.8-1.0"] += 1
        
        return EvaluationMetrics(
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            average_score=average_score,
            score_distribution=score_ranges,
            timestamp=datetime.now()
        )
    
    def save_results(self, results: List[EvaluationResult], filename: Optional[str] = None) -> str:
        """
        Save evaluation results to a JSON file.
        
        Args:
            results: List of EvaluationResult objects to save.
            filename: Optional filename. If None, generates timestamp-based name.
            
        Returns:
            Path to the saved file.
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"evaluation_results_{timestamp}.json"
        
        filepath = self.results_dir / filename
        
        # Convert results to serializable format
        serializable_results = []
        for result in results:
            result_dict = asdict(result)
            result_dict['timestamp'] = result.timestamp.isoformat()
            serializable_results.append(result_dict)
        
        with open(filepath, 'w') as f:
            json.dump(serializable_results, f, indent=2)
        
        logger.info(f"Saved {len(results)} evaluation results to {filepath}")
        return str(filepath)
    
    def generate_report(self, results: List[EvaluationResult], metrics: EvaluationMetrics) -> str:
        """
        Generate a human-readable evaluation report.
        
        Args:
            results: List of EvaluationResult objects.
            metrics: EvaluationMetrics object.
            
        Returns:
            Formatted report string.
        """
        report = f"""
# AI Prompt Evaluation Report

**Generated**: {metrics.timestamp.strftime("%Y-%m-%d %H:%M:%S")}

## Summary Metrics
- **Total Tests**: {metrics.total_tests}
- **Passed Tests**: {metrics.passed_tests} ({metrics.passed_tests/metrics.total_tests*100:.1f}%)
- **Failed Tests**: {metrics.failed_tests} ({metrics.failed_tests/metrics.total_tests*100:.1f}%)
- **Average Score**: {metrics.average_score:.3f}

## Score Distribution
"""
        
        for score_range, count in metrics.score_distribution.items():
            percentage = (count / metrics.total_tests * 100) if metrics.total_tests > 0 else 0
            report += f"- **{score_range}**: {count} tests ({percentage:.1f}%)\n"
        
        report += "\n## Individual Test Results\n"
        
        for result in sorted(results, key=lambda x: x.score, reverse=True):
            status = "✅ PASS" if result.score >= 0.7 else "❌ FAIL"
            report += f"\n### {result.test_case_id} - {status} (Score: {result.score:.3f})\n"
            report += f"**Query**: {result.input_query[:100]}{'...' if len(result.input_query) > 100 else ''}\n"
            report += f"**Response**: {result.actual_response[:200]}{'...' if len(result.actual_response) > 200 else ''}\n"
        
        return report


def main():
    """Example usage of the PromptEvaluator."""
    try:
        evaluator = PromptEvaluator()
        
        # Example system prompt (from main.py)
        system_prompt = """You are an AI assistant specialized in helping developers learn and implement AI solutions using C# and .NET. Your expertise includes:

**Core Responsibilities:**
- Guide developers through AI/ML concepts using .NET frameworks (ML.NET, Semantic Kernel, Azure AI services)
- Translate Python AI examples and tutorials into equivalent C#/.NET code
- Provide practical, working code examples with proper error handling and security best practices
- Explain AI concepts in the context of .NET development patterns and conventions

**When answering questions:**
1. Prioritize answers from the Microsoft Learn documentation, starting with the learn.microsoft.com/*/dotnet/ai content
2. Search the knowledge base for relevant documents, prioritizing content from microsoft.com urls
3. If no relevant documents are found, answer using a web search tool to find up-to-date information
4. Only answer questions based on the context provided by the above instructions
5. Answer succinctly and clearly, avoiding unnecessary complexity unless asked for advanced details
6. Provide links to relevant content using a markdown format like [link text](url)"""
        
        # Example test cases
        test_cases = [
            {
                "id": "semantic_kernel_basic",
                "input": "How do I create a basic Semantic Kernel application in C#?",
                "criteria": "accuracy",
                "metadata": {"category": "semantic_kernel", "difficulty": "beginner"}
            },
            {
                "id": "ml_net_example",
                "input": "Show me how to create a sentiment analysis model with ML.NET",
                "criteria": "code_correctness",
                "metadata": {"category": "ml_net", "difficulty": "intermediate"}
            }
        ]
        
        # Run evaluation
        results = evaluator.run_evaluation_suite("csharp_ai_buddy_v1", system_prompt, test_cases)
        
        # Calculate metrics and generate report
        metrics = evaluator.calculate_metrics(results)
        report = evaluator.generate_report(results, metrics)
        
        # Save results
        results_file = evaluator.save_results(results)
        
        print("Evaluation completed!")
        print(f"Results saved to: {results_file}")
        print("\n" + report)
        
    except Exception as e:
        logger.error(f"Error running evaluation: {e}")


if __name__ == "__main__":
    main()