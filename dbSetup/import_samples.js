// MongoDB Shell Script to Import Sample Data
// Run this script in mongosh with: mongosh <connection_string> --file import_samples.js

// Sample data from sample_data.json
const sampleData = [
  {
    "id": "sample-1",
    "title": "Microsoft.Extensions.AI (Preview)",
    "description": "A core set of .NET libraries including Semantic Kernel, providing unified abstractions for accessing AI services such as LLMs, SLMs, and embeddings in .NET applications.",
    "preview": "./templates/images/ai-extensions.png",
    "authorUrl": "https://github.com/dotnet/ai-samples",
    "author": "Microsoft .NET Team",
    "source": "https://github.com/dotnet/ai-samples/tree/main/src/microsoft-extensions-ai",
    "tags": ["AI", ".NET/C#", "SDK", "Semantic Kernel", "LLM", "msft"]
  },
  {
    "id": "sample-2",
    "title": "Microsoft.Extensions.AI.Evaluation (Preview)",
    "description": "A .NET library to evaluate quality and efficacy of LLM responses in .NET-based intelligent applications.",
    "preview": "./templates/images/ai-evaluation.png",
    "authorUrl": "https://github.com/dotnet/ai-samples",
    "author": "Microsoft .NET Team",
    "source": "https://github.com/dotnet/ai-samples/tree/main/src/microsoft-extensions-ai-evaluation",
    "tags": ["AI", ".NET/C#", "Evaluation", "LLM", "msft"]
  },
  {
    "id": "sample-3",
    "title": "Text Summary Quickstart (OpenAI)",
    "description": "A project sample showing how to summarize text using OpenAI services in .NET.",
    "preview": "./templates/images/sample-summary-openai.png",
    "authorUrl": "https://github.com/dotnet/ai-samples",
    "author": "Microsoft .NET Team",
    "source": "https://github.com/dotnet/ai-samples/tree/main/src/quickstarts/openai/extensions-ai/01-HikeBenefitsSummary",
    "tags": ["AI", ".NET/C#", "OpenAI", "Sample", "Summarization", "msft"]
  },
  {
    "id": "sample-4",
    "title": "Chat App Quickstart (OpenAI)",
    "description": "A chat application example built with .NET using OpenAI for conversational response.",
    "preview": "./templates/images/sample-chat-openai.png",
    "authorUrl": "https://github.com/dotnet/ai-samples",
    "author": "Microsoft .NET Team",
    "source": "https://github.com/dotnet/ai-samples/tree/main/src/quickstarts/openai/extensions-ai/02-build-chat-app/openai",
    "tags": ["AI", ".NET/C#", "OpenAI", "Chatbot", "msft"]
  },
  {
    "id": "sample-5",
    "title": "Function Calling Quickstart (OpenAI)",
    "description": "A practical example of implementing function calling with OpenAI in .NET applications.",
    "preview": "./templates/images/sample-function-calling-openai.png",
    "authorUrl": "https://github.com/dotnet/ai-samples",
    "author": "Microsoft .NET Team",
    "source": "https://github.com/dotnet/ai-samples/tree/main/src/quickstarts/openai/extensions-ai/04-function-calling/openai",
    "tags": ["AI", ".NET/C#", "OpenAI", "Function Calling", "Sample", "msft"]
  },
  {
    "id": "sample-6",
    "title": "Text Summary Quickstart (Azure OpenAI)",
    "description": "Sample project demonstrating text summarization using Azure OpenAI SDK with .NET.",
    "preview": "./templates/images/sample-summary-azure-openai.png",
    "authorUrl": "https://github.com/dotnet/ai-samples",
    "author": "Microsoft .NET Team",
    "source": "https://github.com/dotnet/ai-samples/tree/main/src/quickstarts/azure-openai/extensions-ai/01-HikeBenefitsSummary",
    "tags": ["AI", ".NET/C#", "Azure OpenAI", "Sample", "Summarization", "msft"]
  },
  {
    "id": "sample-7",
    "title": "Customer Support Chat Sample",
    "description": "A sample chat application for customer support scenarios leveraging LLMs in .NET.",
    "preview": "./templates/images/customer-support-chat.png",
    "authorUrl": "https://github.com/dotnet/ai-samples",
    "author": "Microsoft .NET Team",
    "source": "https://github.com/dotnet/ai-samples/tree/main/src/chat/CustomerSupport",
    "tags": ["AI", ".NET/C#", "LLM", "Chat", "Sample", "msft"]
  },
  {
    "id": "sample-8",
    "title": "Generative AI for Beginners (.NET)",
    "description": "A series of five lessons and projects that teach generative AI using the OpenAI API within .NET console apps.",
    "preview": "./templates/images/generative-ai-beginners.png",
    "authorUrl": "https://github.com/microsoft/Generative-AI-for-beginners-dotnet",
    "author": "Microsoft",
    "source": "https://github.com/microsoft/Generative-AI-for-beginners-dotnet",
    "tags": ["AI", ".NET/C#", "Generative AI", "OpenAI", "Beginner", "msft"]
  },
  {
    "id": "sample-9",
    "title": "eShopLite - Semantic Search .NET AI Sample",
    "description": "Reference .NET eCommerce app showing Semantic Search using Azure AI Search service.",
    "preview": "./templates/images/sample-eshop.png",
    "authorUrl": "https://github.com/BrunoCapuano",
    "author": "Bruno Capuano",
    "source": "https://github.com/Microsoft/eshoplite-semantic-search",
    "tags": ["AI", "Azure AI Search", ".NET/C#", "Semantic Search", "Reference App", "msft"]
  },
  {
    "id": "sample-10",
    "title": "eShopSupport – AI-Enhanced Customer Support Sample",
    "description": "A comprehensive intelligent app sample demonstrating semantic search, summarization, classification, Q&A chatbot, sentiment analysis, data generation, evaluation tools, and E2E testing. Shows how to infuse real-world AI features into a modern .NET Aspire line-of-business app.",
    "preview": "./templates/images/sample-eshopsupport.png",
    "authorUrl": "https://github.com/dotnet",
    "author": "Microsoft .NET Team",
    "source": "https://github.com/dotnet/eshopsupport",
    "tags": ["AI", ".NET/C#", "Semantic Search", "Summarization", "Classification", "Chatbot", "Sentiment", "E2E Testing", "Azure", "msft"]
  },
  {
    "id": "sample-11",
    "title": "OllamaSharp + Microsoft.Extensions.AI (Local LLM, GPT-OSS)",
    "description": "Sample showing how to use the open-weight GPT-OSS model with Ollama and .NET—build private, fast, and offline-capable AI features with Microsoft.Extensions.AI and OllamaSharp.",
    "preview": "./templates/images/sample-ollama.png",
    "authorUrl": "https://github.com/ollama/ollama",
    "author": "Ollama, Microsoft",
    "source": "https://github.com/ollama/ollama",
    "tags": ["AI", ".NET/C#", "Ollama", "LLM", "GPT-OSS", "Local Models", "Sample"]
  },
  {
    "id": "sample-12",
    "title": "eShopLite + GitHub Copilot Coding Agent",
    "description": "A streamlined .NET sample used to demonstrate GitHub Copilot Coding Agent: automates unit tests, feature creation from PRDs, and GitHub issue/PR management in .NET solutions.",
    "preview": "./templates/images/sample-eshoplite-copilot.png",
    "authorUrl": "https://github.com/Azure-Samples/eShopLite",
    "author": "Microsoft, Copilot Team",
    "source": "https://aka.ms/eShopLite/repo",
    "tags": ["AI", ".NET/C#", "Copilot", "Automation", "Unit Testing", "Sample", "msft"]
  },
  {
    "id": "sample-13",
    "title": "Microsoft.Extensions.AI.Evaluation Usage Examples",
    "description": "Sample projects showing how to use the Microsoft.Extensions.AI.Evaluation libraries including new agent quality, NLP, and content safety evaluators for LLM outputs.",
    "preview": "./templates/images/sample-aieval.png",
    "authorUrl": "https://github.com/dotnet",
    "author": "Microsoft .NET Team",
    "source": "https://github.com/dotnet/ai-samples/tree/main/src/microsoft-extensions-ai-evaluation",
    "tags": ["AI", ".NET/C#", "LLM", "NLP", "Evaluation", "Content Safety", "Sample", "msft"]
  },
  {
    "id": "sample-14",
    "title": "AI-powered Test Data Generators",
    "description": "Realistic, AI-powered tools for large volumes of test data generation in .NET. Automates the creation of category, brand, and other seed data via LLM prompts.",
    "preview": "./templates/images/test-data-gen.png",
    "authorUrl": "https://github.com/dotnet",
    "author": "Microsoft .NET Team",
    "source": "https://github.com/dotnet/eShopSupport/tree/main/seeddata/DataGenerator/Generators",
    "tags": ["AI", ".NET/C#", "Test Data", "Generation", "Seed Data", "Sample", "msft"]
  },
  {
    "id": "sample-15",
    "title": "eShopSupport - Ticket Summarizer Service",
    "description": "A backend service for automatic summarization and sentiment scoring of customer support tickets using LLMs.",
    "preview": "./templates/images/ticket-summarizer.png",
    "authorUrl": "https://github.com/dotnet",
    "author": "Microsoft .NET Team",
    "source": "https://github.com/dotnet/eShopSupport/blob/main/src/Backend/Services/TicketSummarizer.cs",
    "tags": ["AI", ".NET/C#", "Summarization", "Sentiment Analysis", "Backend", "msft"]
  },
  {
    "id": "sample-16",
    "title": "Semantic Kernel Main Samples for .NET",
    "description": "Comprehensive Semantic Kernel samples for .NET, covering chat completion, embeddings, function calling, hybrid model orchestration, agent frameworks, and Microsoft.Extensions.AI integration.",
    "preview": "./templates/images/sample-semantic-kernel-main.png",
    "authorUrl": "https://github.com/microsoft/semantic-kernel",
    "author": "Microsoft Semantic Kernel Team",
    "source": "https://github.com/microsoft/semantic-kernel/tree/main/dotnet/samples",
    "tags": ["AI", ".NET/C#", "Semantic Kernel", "LLM", "Embeddings", "Agents", "Hybrid Orchestration", "Microsoft.Extensions.AI", "Sample"]
  },
  {
    "id": "sample-17",
    "title": "Chat Completion with Audio (OpenAI GPT-4o-preview + Semantic Kernel)",
    "description": "Sample showing how to use OpenAI's gpt-4o-audio-preview model for both audio input and output chat completions in .NET with Semantic Kernel.",
    "preview": "./templates/images/sample-audio-preview-sk.png",
    "authorUrl": "https://github.com/microsoft/semantic-kernel",
    "author": "Microsoft Semantic Kernel Team",
    "source": "https://github.com/microsoft/semantic-kernel/blob/main/dotnet/samples/Concepts/ChatCompletion/OpenAI_ChatCompletionWithAudio.cs",
    "tags": [".NET/C#", "Semantic Kernel", "OpenAI", "Audio", "Chat Completion", "Sample"]
  },
  {
    "id": "sample-18",
    "title": "Hybrid Model Orchestration Sample (FallbackChatClient)",
    "description": "Sample for orchestrating multiple LLM providers (local/cloud) using a fallback-based chat client for enhanced reliability. Implements hybrid model patterns in .NET apps with Semantic Kernel.",
    "preview": "./templates/images/sample-hybrid-fallback.png",
    "authorUrl": "https://github.com/microsoft/semantic-kernel",
    "author": "Microsoft Semantic Kernel Team",
    "source": "https://github.com/microsoft/semantic-kernel/blob/main/dotnet/samples/Concepts/ChatCompletion/HybridCompletion_Fallback.cs",
    "tags": [".NET/C#", "Semantic Kernel", "Hybrid Model", "LLM", "Fallback", "Sample"]
  },
  {
    "id": "sample-19",
    "title": "Model Context Protocol (MCP) Server Demo with Semantic Kernel",
    "description": "Demonstrates building a Model Context Protocol server in C# that exposes Semantic Kernel plugins as MCP-compatible AI tools, enabling cross-platform and multi-agent integration.",
    "preview": "./templates/images/sample-mcp-server.png",
    "authorUrl": "https://github.com/microsoft/semantic-kernel",
    "author": "Microsoft Semantic Kernel Team",
    "source": "https://github.com/microsoft/semantic-kernel/tree/main/dotnet/samples/Demos/ModelContextProtocolClientServer",
    "tags": ["AI", ".NET/C#", "Semantic Kernel", "MCP", "Server", "Cross-platform", "Sample"]
  }
];

// Connect to the database (assumes you've already connected to the correct database)
print("🚀 Importing C# AI Buddy Sample Data...");
print("=" * 50);

// Switch to your database (replace 'your_database_name' with actual database name)
// use your_database_name;

// Get the samples collection
const samplesCollection = db.samples;

// Optional: Clear existing samples (uncomment if you want to start fresh)
// print("🗑️  Clearing existing samples...");
// const deleteResult = samplesCollection.deleteMany({});
// print(`Deleted ${deleteResult.deletedCount} existing samples`);

// Insert the sample data
print("📥 Inserting sample data...");
const insertResult = samplesCollection.insertMany(sampleData);
print(`✅ Successfully inserted ${insertResult.insertedIds.length} samples`);

// Create indexes for better performance
print("📊 Creating database indexes...");
try {
  samplesCollection.createIndex({ "id": 1 }, { unique: true });
  samplesCollection.createIndex({ "title": 1 });
  samplesCollection.createIndex({ "tags": 1 });
  samplesCollection.createIndex({ "author": 1 });
  print("✅ Indexes created successfully");
} catch (error) {
  print(`⚠️  Index creation warning: ${error.message}`);
}

// Print summary statistics
const totalSamples = samplesCollection.countDocuments({});
const microsoftSamples = samplesCollection.countDocuments({ "tags": "msft" });
const uniqueTags = samplesCollection.distinct("tags");
const uniqueAuthors = samplesCollection.distinct("author");

print("\n" + "=" * 50);
print("📈 DATABASE SUMMARY");
print("=" * 50);
print(`Total samples: ${totalSamples}`);
print(`Microsoft authored samples: ${microsoftSamples}`);
print(`Unique authors: ${uniqueAuthors.length}`);
print(`Unique tags: ${uniqueTags.length}`);
print(`Tags: ${uniqueTags.sort().join(", ")}`);

// Show sample titles
print("\nSample titles (first 5):");
const sampleTitles = samplesCollection.find({}, { title: 1, _id: 0 }).limit(5);
let counter = 1;
sampleTitles.forEach(doc => {
  print(`  ${counter}. ${doc.title}`);
  counter++;
});

print("\n✅ Sample data import completed!");
print("🌐 You can now test the API at: /api/samples");