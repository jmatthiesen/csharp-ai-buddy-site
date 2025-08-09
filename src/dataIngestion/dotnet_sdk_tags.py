"""
.NET Framework Tags for RAG Pipeline
Simplified tagging system using AI for categorization during ingestion.
"""

# Core framework categories
FRAMEWORK_CATEGORIES = [
    "Microsoft.Extensions.AI",
    "ML.NET",
    "AutoGen",
    "Semantic Kernel",
    "Semantic Kernel Agents",
    "Semantic Kernel Process Framework",
    "OpenAI SDK",
]

# Semantic Kernel sub-frameworks (these will get both their specific tag and "Semantic Kernel")
SEMANTIC_KERNEL_FRAMEWORKS = ["Semantic Kernel Agents", "Semantic Kernel Process Framework"]


def get_framework_categories() -> list:
    """Get all available framework categories."""
    return FRAMEWORK_CATEGORIES.copy()


def is_semantic_kernel_framework(framework: str) -> bool:
    """Check if a framework is part of the Semantic Kernel family."""
    return framework in SEMANTIC_KERNEL_FRAMEWORKS


def get_semantic_kernel_frameworks() -> list:
    """Get all Semantic Kernel sub-frameworks."""
    return SEMANTIC_KERNEL_FRAMEWORKS.copy()


def categorize_with_ai(content: str, openai_client) -> list:
    """
    Use AI to categorize content and identify relevant frameworks.

    Args:
        content: The content to categorize
        openai_client: OpenAI client instance

    Returns:
        List of framework tags identified in the content
    """
    try:
        # Create a prompt for AI categorization
        prompt = f"""
        Analyze the following .NET AI development content and identify which frameworks it relates to.
        
        Available framework categories:
        - Microsoft.Extensions.AI
        - ML.NET
        - AutoGen
        - Semantic Kernel
        - Semantic Kernel Agents
        - Semantic Kernel Process Framework
        - OpenAI SDK
        
        Rules:
        1. Only return framework names that are clearly mentioned or implied in the content
        2. If content mentions Semantic Kernel Agents or Semantic Kernel Process Framework, also include "Semantic Kernel"
        3. Return only the framework names, separated by commas
        4. If no frameworks are detected, return "None"
        
        Content to analyze:
        {content[:2000]}  # Limit content length for API call
        
        Frameworks detected:
        """

        response = openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that categorizes .NET AI development content. Return only framework names separated by commas.",
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=100,
            temperature=0.1,
        )

        # Parse the response
        frameworks_text = response.choices[0].message.content.strip()

        if frameworks_text.lower() == "none":
            return []

        # Split by comma and clean up
        frameworks = [f.strip() for f in frameworks_text.split(",") if f.strip()]

        # Validate frameworks against our known categories
        valid_frameworks = []
        for framework in frameworks:
            if framework in FRAMEWORK_CATEGORIES:
                valid_frameworks.append(framework)
                # Add Semantic Kernel tag for sub-frameworks
                if is_semantic_kernel_framework(framework):
                    if "Semantic Kernel" not in valid_frameworks:
                        valid_frameworks.append("Semantic Kernel")

        return valid_frameworks

    except Exception as e:
        print(f"Error in AI categorization: {e}")
        return []


def suggest_tags_simple(content: str) -> list:
    """
    Simple keyword-based tagging as fallback when AI is not available.
    This is a basic implementation for when AI categorization fails.
    """
    content_lower = content.lower()
    suggested_tags = []

    # Simple keyword matching
    if "semantic kernel" in content_lower:
        suggested_tags.append("Semantic Kernel")

        if "agent" in content_lower:
            suggested_tags.append("Semantic Kernel Agents")
        elif "process" in content_lower:
            suggested_tags.append("Semantic Kernel Process Framework")

    if "microsoft.extensions.ai" in content_lower or "extensions.ai" in content_lower:
        suggested_tags.append("Microsoft.Extensions.AI")

    if "ml.net" in content_lower or "microsoft.ml" in content_lower:
        suggested_tags.append("ML.NET")

    if "autogen" in content_lower:
        suggested_tags.append("AutoGen")

    if "openai" in content_lower and "sdk" in content_lower:
        suggested_tags.append("OpenAI SDK")

    return suggested_tags


def validate_framework_tags(tags: list) -> tuple[list, list]:
    """
    Validate framework tags and return valid and invalid tags.

    Returns:
        tuple: (valid_tags, invalid_tags)
    """
    valid_tags = []
    invalid_tags = []

    for tag in tags:
        if tag in FRAMEWORK_CATEGORIES:
            valid_tags.append(tag)
        else:
            invalid_tags.append(tag)

    return valid_tags, invalid_tags
