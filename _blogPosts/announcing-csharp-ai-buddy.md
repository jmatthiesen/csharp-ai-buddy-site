# Announcing C# AI Buddy: Your Assistant for Building AI Solutions with .NET

Over the past few months, I've been building something I wish existed when I started working with AI in .NET: a tool that helps C# developers cut through the noise and build AI-powered applications faster. Today, I'm excited to share C# AI Buddy in early preview.

**Want to try it out?** You can get started right away at [csharpaibuddy.com](https://csharpaibuddy.com) using the preview key: `PREVIEW2025`

![C# AI Buddy Screenshot](placeholder-for-screenshot.png)

## Why I Built This

I've always been passionate about helping other developers learn and grow. Whether it's through blog posts, sample code, or conversations with colleagues, I love sharing what I've learned. But as I dove deeper into the .NET AI ecosystem, I noticed something: the landscape is fragmented.

Should you use Semantic Kernel? ML.NET? AutoGen? Microsoft.Extensions.AI? OpenAI's SDK directly? What about Azure OpenAI vs. OpenAI vs. Anthropic? And which .NET version should you target?

Every project I started, I'd spend hours researching the same questions, reading through documentation, and trying to figure out which approach was best for my use case. I realized I wasn't alone - many C# developers face this same decision paralysis when trying to build AI solutions.

That's when I decided to build C# AI Buddy. Not just as a tool for myself, but as a way to help the entire .NET community navigate this rapidly evolving space. And along the way, I'd level up my own skills in building production AI systems.

## The Goal: Cut Development Time in Half

Here's my ambitious goal for C# AI Buddy: **help C# developers cut their AI development time in half**.

Instead of spending hours searching through documentation, blog posts, and GitHub repos, you can ask questions and get context-aware answers tailored to your specific stack. Want to know how to implement image classification with ML.NET on .NET 9? Ask. Need to understand the differences between Semantic Kernel and AutoGen for your use case? Just ask.

The system doesn't just answer questions - it provides:
- **Context-aware guidance** based on your chosen .NET version, AI library, and provider
- **Curated code samples** from across the .NET AI ecosystem
- **Latest news and articles** about .NET AI development
- **NuGet package recommendations** with documentation links

All in one place, with real-time streaming responses so you're not sitting around waiting for answers.

## What C# AI Buddy Does

Let me walk you through the core functionality:

### AI Chat Assistant

The heart of C# AI Buddy is the conversational AI chat interface. You can ask questions about any aspect of building AI solutions with C# and .NET. The system uses OpenAI's latest models combined with a curated knowledge base of .NET AI documentation, blog posts, and official resources.

What makes it unique is the filter system. Before you ask a question, you can tell the AI what you're working with:
- **.NET Version**: .NET 7, 8, or 9
- **AI Library**: Semantic Kernel, ML.NET, AutoGen, Microsoft.Extensions.AI, or others
- **AI Provider**: OpenAI, Azure OpenAI, Anthropic, Google, or local models

This context helps the AI provide more relevant answers and code examples that actually match your environment.

### Code Samples Gallery

I've been aggregating code samples from across the .NET AI community - GitHub repos, blog posts, official Microsoft samples, and more. You can browse by framework, search for specific patterns, and find working examples to learn from.

Each sample includes author attribution, source links, and tags so you can quickly filter to what matters for your project.

### .NET AI News Feed

Keeping up with the latest developments in the .NET AI space is exhausting. C# AI Buddy automatically monitors RSS feeds from Microsoft DevBlogs, community blogs, and other sources to bring you the latest articles and announcements.

Each article includes an AI-generated summary, so you can quickly decide if it's worth diving deeper.

### Feedback Loop

One of my favorite features is the thumbs up/down feedback system. Every AI response can be rated, and I'm using that feedback to continuously improve the quality of answers. This is powered by Arize Phoenix for observability, which lets me see what's working and what needs improvement.

## Try It Today: Preview Key Inside

I'm opening up C# AI Buddy for early preview access today. You can start using it right now at [csharpaibuddy.com](https://csharpaibuddy.com) with the preview key:

**`PREVIEW2025`**

Just enter that key when prompted, and you'll have full access to all features. I'd love to hear what you think - what works well, what doesn't, and what features you'd like to see added.

## A Note on Technology Choices

You might notice something interesting about this project: it's built primarily with Python, not .NET. The backend uses FastAPI, the data ingestion pipeline is Python-based, and I'm leveraging the rich Python AI ecosystem.

Why? Honestly, it came down to pragmatism. When I started this project, I wanted to use the OpenAI Agents SDK for multi-agent orchestration, and at the time, the Python version was significantly more mature than the .NET offerings. The Python ecosystem also has incredible tooling for vector search, embeddings, and document processing.

That said, this is a tool *for* .NET developers, built by a .NET developer. The knowledge base is entirely focused on C# and .NET AI development. And who knows - maybe a future version will be a full .NET rewrite once the ecosystem matures a bit more. For now, I'm focused on delivering value to the community, regardless of what tech stack powers it behind the scenes.

## Join Me in the Code

One of my core goals with this project is to learn in public and invite others to learn alongside me. The entire codebase is open source and available on GitHub at [github.com/jordanmatthiesen/csharp-ai-buddy-site](https://github.com/jordanmatthiesen/csharp-ai-buddy-site).

Whether you're curious about how to build production AI systems, want to understand vector search with MongoDB, or just want to see how FastAPI's streaming responses work, the code is there for you to explore.

And if you want to contribute? Even better! I'd love help adding more content sources to the data ingestion pipeline, improving the AI prompts, adding new features, or expanding the code samples gallery. This is a community project at heart.

Here's what you'll find in the repo:
- **FastAPI backend** with streaming AI responses using OpenAI Agents SDK
- **MongoDB vector search** for semantic document retrieval
- **Data ingestion pipeline** that automatically processes web content, blog posts, and RSS feeds
- **OpenTelemetry instrumentation** for observability
- **Arize integration** for feedback tracking and continuous improvement
- **Comprehensive documentation** including architecture guides and deployment instructions

If you're interested in learning how these pieces fit together, clone the repo and dig in. I've tried to document everything thoroughly, and I'm happy to answer questions.

## What's Next?

This is just the beginning. I've got a long list of features and improvements I'm excited to build:
- Expanded code samples from more community sources
- Better filtering and search capabilities
- Conversation history and saved chats
- More AI providers and frameworks
- Community contributions and curated content

But I need your help to prioritize. What would make C# AI Buddy more valuable for you? What questions does it answer poorly today? What features would you use every day?

## Get Started Today

Ready to try it out? Head over to [csharpaibuddy.com](https://csharpaibuddy.com) and use the preview key **`PREVIEW2025`** to get started. Ask it anything about building AI solutions with C# and .NET.

And if you find it useful, I'd love to hear about it. Leave feedback directly in the app, open an issue on GitHub, or reach out to me directly. This project is all about learning together and making .NET AI development more accessible for everyone.

Let's build the future of AI with C# together.

---

*Want to dive into the code? Check out the [GitHub repository](https://github.com/jordanmatthiesen/csharp-ai-buddy-site) to see how it's built and contribute your own improvements.*
