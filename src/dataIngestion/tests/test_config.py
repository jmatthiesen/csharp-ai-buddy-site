"""
Test configuration and test data for RAG Data Ingestion Pipeline tests.
"""

# Test content samples for different frameworks
TEST_CONTENT_SAMPLES = {
    "semantic_kernel": {
        "title": "Semantic Kernel Tutorial",
        "content": """
        # Getting Started with Semantic Kernel
        
        Semantic Kernel is Microsoft's AI orchestration library for .NET.
        Learn how to build AI applications with Semantic Kernel.
        
        ## Installation
        
        ```bash
        dotnet add package Microsoft.SemanticKernel
        ```
        
        ## Basic Usage
        
        ```csharp
        var kernel = Kernel.CreateBuilder()
            .AddOpenAIChatCompletion("gpt-4", "your-api-key")
            .Build();
        
        var result = await kernel.InvokePromptAsync("Hello, how are you?");
        ```
        """,
        "expected_tags": ["Semantic Kernel"],
    },
    "ml_net": {
        "title": "ML.NET Machine Learning",
        "content": """
        # ML.NET Tutorial
        
        ML.NET is Microsoft's machine learning framework for .NET developers.
        Build custom ML models with C# and F#.
        
        ## Setup
        
        ```bash
        dotnet add package Microsoft.ML
        dotnet add package Microsoft.ML.FastTree
        ```
        
        ## Example
        
        ```csharp
        var mlContext = new MLContext();
        var dataView = mlContext.Data.LoadFromTextFile<SentimentData>("data.csv");
        
        var pipeline = mlContext.Transforms.Text
            .FeaturizeText("Features", "SentimentText")
            .Append(mlContext.BinaryClassification.Trainers.FastTree());
        
        var model = pipeline.Fit(dataView);
        ```
        """,
        "expected_tags": ["ML.NET"],
    },
    "semantic_kernel_agents": {
        "title": "Semantic Kernel Agents",
        "content": """
        # Building AI Agents with Semantic Kernel Agents
        
        Semantic Kernel Agents provides a powerful framework for building intelligent agents.
        Create multi-agent conversations and workflows.
        
        ## Installation
        
        ```bash
        dotnet add package Microsoft.SemanticKernel.Agents
        ```
        
        ## Creating Agents
        
        ```csharp
        var agent = new ChatCompletionAgent(kernel, "You are a helpful assistant.");
        var result = await agent.InvokeAsync("What is the weather?");
        ```
        
        ## Multi-Agent Conversations
        
        ```csharp
        var agent1 = new ChatCompletionAgent(kernel, "You are a data analyst.");
        var agent2 = new ChatCompletionAgent(kernel, "You are a business consultant.");
        
        var group = new AgentGroup(agent1, agent2);
        var result = await group.InvokeAsync("Analyze this sales data.");
        ```
        """,
        "expected_tags": ["Semantic Kernel Agents", "Semantic Kernel"],
    },
    "microsoft_extensions_ai": {
        "title": "Microsoft.Extensions.AI",
        "content": """
        # Microsoft.Extensions.AI
        
        Microsoft.Extensions.AI provides AI extensions for .NET applications.
        Integrate AI services easily with dependency injection.
        
        ## Setup
        
        ```bash
        dotnet add package Microsoft.Extensions.AI
        ```
        
        ## Usage
        
        ```csharp
        var builder = WebApplication.CreateBuilder(args);
        builder.Services.AddOpenAIClient();
        
        var app = builder.Build();
        ```
        """,
        "expected_tags": ["Microsoft.Extensions.AI"],
    },
    "autogen": {
        "title": "AutoGen Framework",
        "content": """
        # AutoGen for .NET
        
        AutoGen is Microsoft's framework for building AI agents.
        Create conversational AI applications with ease.
        
        ## Installation
        
        ```bash
        dotnet add package Microsoft.AutoGen
        ```
        
        ## Example
        
        ```csharp
        var agent = new ConversationalAgent("You are a helpful assistant.");
        var response = await agent.SendMessageAsync("Hello!");
        ```
        """,
        "expected_tags": ["AutoGen"],
    },
    "openai_sdk": {
        "title": "OpenAI SDK for .NET",
        "content": """
        # OpenAI SDK for .NET
        
        Official OpenAI SDK for .NET applications.
        Integrate OpenAI services directly in your C# code.
        
        ## Installation
        
        ```bash
        dotnet add package OpenAI
        ```
        
        ## Usage
        
        ```csharp
        var client = new OpenAIClient("your-api-key");
        var response = await client.GetChatCompletionsAsync("gpt-4", "Hello!");
        ```
        """,
        "expected_tags": ["OpenAI SDK"],
    },
}

# Expected framework categories
EXPECTED_FRAMEWORK_CATEGORIES = [
    "Microsoft.Extensions.AI",
    "ML.NET",
    "AutoGen",
    "Semantic Kernel",
    "Semantic Kernel Agents",
    "Semantic Kernel Process Framework",
    "OpenAI SDK",
]

# Test configuration
TEST_CONFIG = {
    "openai_model": "gpt-3.5-turbo",
    "max_tokens": 100,
    "temperature": 0.1,
    "timeout_seconds": 30,
    "retry_attempts": 3,
}

# Validation rules for AI categorization
VALIDATION_RULES = {
    "semantic_kernel_family": {
        "description": "Semantic Kernel sub-frameworks should include both specific and parent tags",
        "rules": [
            "Semantic Kernel Agents → ['Semantic Kernel Agents', 'Semantic Kernel']",
            "Semantic Kernel Process Framework → ['Semantic Kernel Process Framework', 'Semantic Kernel']",
        ],
    },
    "content_length": {
        "description": "Content should be truncated to reasonable length for API calls",
        "max_length": 2000,
    },
    "response_format": {
        "description": "AI responses should be comma-separated framework names",
        "examples": ["Semantic Kernel", "ML.NET, Microsoft.Extensions.AI", "None"],
    },
}
