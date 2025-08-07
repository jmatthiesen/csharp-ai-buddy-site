#!/usr/bin/env python3
"""
Comprehensive evaluation runner for C# AI Buddy prompts.

This script orchestrates the evaluation of all prompts used in the application,
including the main AI assistant prompt and the AI categorization prompts.
"""

import os
import sys
import json
import asyncio
from dotenv import load_dotenv
from pathlib import Path
from typing import Dict, List, Any
import argparse
import logging

load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evals.prompt_evaluator import PromptEvaluator, EvaluationResult, EvaluationMetrics
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../dataIngestion")))
# Removed import - now using Responses API directly
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComprehensiveEvaluationRunner:
    """
    Runs comprehensive evaluations across all AI components of the application.
    """
    
    def __init__(self, api_key: str = None):
        """Initialize the evaluation runner."""
        self.evaluator = PromptEvaluator(api_key)
        self.results_dir = Path("evals/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Load system prompts
        self.main_assistant_prompt = self._load_main_assistant_prompt()
    
    def _load_main_assistant_prompt(self) -> str:
        """Load the main AI assistant system prompt from main.py."""
        return """You are an AI assistant specialized in helping developers learn and implement AI solutions using C# and .NET. Your expertise includes:

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
    
    def run_main_assistant_evaluation(self) -> List[EvaluationResult]:
        """Run evaluation for the main AI assistant prompt."""
        logger.info("Running main AI assistant prompt evaluation...")
        
        test_cases_file = "evals/test_cases/csharp_ai_buddy_tests.json"
        test_cases = self.evaluator.load_test_cases(test_cases_file)
        
        if not test_cases:
            logger.error(f"No test cases loaded from {test_cases_file}")
            return []
        
        results = self.evaluator.run_evaluation_suite(
            prompt_id="main_assistant_v1",
            system_prompt=self.main_assistant_prompt,
            test_cases=test_cases
        )
        
        logger.info(f"Completed main assistant evaluation with {len(results)} test cases")
        return results
    
    def run_categorization_evaluation(self) -> List[EvaluationResult]:
        """Run evaluation for the AI categorization prompt."""
        logger.info("Running AI categorization prompt evaluation...")
        
        test_cases_file = "evals/test_cases/categorization_tests.json"
        test_cases = self.evaluator.load_test_cases(test_cases_file)
        
        if not test_cases:
            logger.error(f"No test cases loaded from {test_cases_file}")
            return []
        
        # Custom evaluation for categorization
        results = []
        client = OpenAI(api_key=self.evaluator.api_key)
        
        for i, test_case in enumerate(test_cases):
            try:
                test_case_id = test_case.get('id', f"categorization_test_{i}")
                content = test_case.get('input', '')
                expected_tags = test_case.get('expected', 'None')
                
                logger.info(f"Running categorization test: {test_case_id}")
                
                # Use the categorization system directly
                from dotnet_sdk_tags import categorize_with_ai
                detected_tags = categorize_with_ai(content, client)
                actual_response = ', '.join(detected_tags) if detected_tags else 'None'
                
                # Calculate accuracy score
                expected_set = set(tag.strip() for tag in expected_tags.split(',') if tag.strip() != 'None')
                actual_set = set(detected_tags)
                
                if not expected_set and not actual_set:
                    # Both empty - perfect match
                    score = 1.0
                elif not expected_set or not actual_set:
                    # One empty, one not - no match
                    score = 0.0
                else:
                    # Calculate Jaccard similarity
                    intersection = len(expected_set.intersection(actual_set))
                    union = len(expected_set.union(actual_set))
                    score = intersection / union if union > 0 else 0.0
                
                result = EvaluationResult(
                    prompt_id="categorization_v1",
                    test_case_id=test_case_id,
                    input_query=content[:200] + "..." if len(content) > 200 else content,
                    expected_response=expected_tags,
                    actual_response=actual_response,
                    score=score,
                    evaluation_criteria="categorization_accuracy",
                    timestamp=self.evaluator.evaluation_results[0].timestamp if self.evaluator.evaluation_results else None,
                    metadata=test_case.get('metadata', {})
                )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Error evaluating categorization test {test_case_id}: {e}")
                continue
        
        logger.info(f"Completed categorization evaluation with {len(results)} test cases")
        return results
    
    def run_all_evaluations(self) -> Dict[str, Any]:
        """Run all evaluations and generate comprehensive report."""
        logger.info("Starting comprehensive evaluation of all AI prompts...")
        
        all_results = {}
        
        # Run main assistant evaluation
        main_results = self.run_main_assistant_evaluation()
        all_results['main_assistant'] = {
            'results': main_results,
            'metrics': self.evaluator.calculate_metrics(main_results) if main_results else None
        }
        
        # Run categorization evaluation
        categorization_results = self.run_categorization_evaluation()
        all_results['categorization'] = {
            'results': categorization_results,
            'metrics': self.evaluator.calculate_metrics(categorization_results) if categorization_results else None
        }
        
        # Generate comprehensive report
        report = self._generate_comprehensive_report(all_results)
        
        # Save all results
        timestamp = all_results['main_assistant']['metrics'].timestamp.strftime("%Y%m%d_%H%M%S") if all_results['main_assistant']['metrics'] else "unknown"
        
        # Save individual result sets
        if main_results:
            main_file = self.evaluator.save_results(main_results, f"main_assistant_results_{timestamp}.json")
            logger.info(f"Main assistant results saved to: {main_file}")
        
        if categorization_results:
            cat_file = self.evaluator.save_results(categorization_results, f"categorization_results_{timestamp}.json")
            logger.info(f"Categorization results saved to: {cat_file}")
        
        # Save comprehensive report
        report_file = self.results_dir / f"comprehensive_report_{timestamp}.md"
        with open(report_file, 'w') as f:
            f.write(report)
        
        logger.info(f"Comprehensive report saved to: {report_file}")
        
        return all_results
    
    def _generate_comprehensive_report(self, all_results: Dict[str, Any]) -> str:
        """Generate a comprehensive evaluation report."""
        report = f"""# Comprehensive AI Prompt Evaluation Report

**Generated**: {all_results['main_assistant']['metrics'].timestamp.strftime("%Y-%m-%d %H:%M:%S") if all_results['main_assistant']['metrics'] else 'Unknown'}

## Executive Summary

This report presents the evaluation results for all AI prompts used in the C# AI Buddy application.

"""
        
        # Main Assistant Results
        if all_results['main_assistant']['metrics']:
            metrics = all_results['main_assistant']['metrics']
            report += f"""## Main AI Assistant Evaluation

### Summary Metrics
- **Total Tests**: {metrics.total_tests}
- **Passed Tests**: {metrics.passed_tests} ({metrics.passed_tests/metrics.total_tests*100:.1f}%)
- **Failed Tests**: {metrics.failed_tests} ({metrics.failed_tests/metrics.total_tests*100:.1f}%)
- **Average Score**: {metrics.average_score:.3f}

### Score Distribution
"""
            for score_range, count in metrics.score_distribution.items():
                percentage = (count / metrics.total_tests * 100) if metrics.total_tests > 0 else 0
                report += f"- **{score_range}**: {count} tests ({percentage:.1f}%)\n"
        
        # Categorization Results
        if all_results['categorization']['metrics']:
            metrics = all_results['categorization']['metrics']
            report += f"""

## AI Categorization Evaluation

### Summary Metrics
- **Total Tests**: {metrics.total_tests}
- **Passed Tests**: {metrics.passed_tests} ({metrics.passed_tests/metrics.total_tests*100:.1f}%)
- **Failed Tests**: {metrics.failed_tests} ({metrics.failed_tests/metrics.total_tests*100:.1f}%)
- **Average Score**: {metrics.average_score:.3f}

### Score Distribution
"""
            for score_range, count in metrics.score_distribution.items():
                percentage = (count / metrics.total_tests * 100) if metrics.total_tests > 0 else 0
                report += f"- **{score_range}**: {count} tests ({percentage:.1f}%)\n"
        
        # Overall Assessment
        main_avg = all_results['main_assistant']['metrics'].average_score if all_results['main_assistant']['metrics'] else 0
        cat_avg = all_results['categorization']['metrics'].average_score if all_results['categorization']['metrics'] else 0
        overall_avg = (main_avg + cat_avg) / 2 if main_avg and cat_avg else main_avg or cat_avg
        
        report += f"""

## Overall Assessment

**Overall Average Score**: {overall_avg:.3f}

### Recommendations

"""
        
        if overall_avg < 0.7:
            report += """- 🔴 **Critical**: Overall performance is below acceptable threshold (0.7)
- Immediate prompt engineering improvements needed
- Consider revising system instructions and examples
"""
        elif overall_avg < 0.8:
            report += """- 🟡 **Warning**: Performance is acceptable but has room for improvement
- Review failed test cases for common patterns
- Consider adding more specific instructions or examples
"""
        else:
            report += """- 🟢 **Good**: Overall performance meets quality standards
- Continue monitoring and maintaining current prompt quality
- Consider running evaluations regularly as part of CI/CD
"""
        
        report += """
### Next Steps

1. **Review Failed Cases**: Analyze individual test cases that scored below 0.7
2. **Prompt Iteration**: Update prompts based on failure patterns
3. **Expand Test Coverage**: Add more test cases for edge cases and new features
4. **Automate Evaluations**: Integrate this evaluation suite into your CI/CD pipeline
5. **Performance Monitoring**: Set up regular evaluation runs to track prompt performance over time
"""
        
        return report


def main():
    """Main entry point for running evaluations."""
    parser = argparse.ArgumentParser(description="Run comprehensive AI prompt evaluations")
    parser.add_argument("--component", choices=["all", "main", "categorization"], 
                       default="all", help="Which component to evaluate")
    parser.add_argument("--api-key", help="OpenAI API key (or set OPENAI_API_KEY env var)")
    
    args = parser.parse_args()
    
    try:
        runner = ComprehensiveEvaluationRunner(args.api_key)
        
        if args.component == "all":
            results = runner.run_all_evaluations()
            print("✅ Comprehensive evaluation completed!")
            
            # Print summary
            if results['main_assistant']['metrics']:
                main_score = results['main_assistant']['metrics'].average_score
                print(f"📊 Main Assistant Average Score: {main_score:.3f}")
            
            if results['categorization']['metrics']:
                cat_score = results['categorization']['metrics'].average_score
                print(f"📊 Categorization Average Score: {cat_score:.3f}")
                
        elif args.component == "main":
            results = runner.run_main_assistant_evaluation()
            metrics = runner.evaluator.calculate_metrics(results)
            print(f"✅ Main assistant evaluation completed!")
            print(f"📊 Average Score: {metrics.average_score:.3f}")
            print(f"📊 Passed: {metrics.passed_tests}/{metrics.total_tests}")
            
        elif args.component == "categorization":
            results = runner.run_categorization_evaluation()
            metrics = runner.evaluator.calculate_metrics(results)
            print(f"✅ Categorization evaluation completed!")
            print(f"📊 Average Score: {metrics.average_score:.3f}")
            print(f"📊 Passed: {metrics.passed_tests}/{metrics.total_tests}")
        
    except Exception as e:
        logger.error(f"Error running evaluations: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()