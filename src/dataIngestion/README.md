# RAG Data Ingestion Pipeline

A Python-based data ingestion pipeline for Retrieval-Augmented Generation (RAG) solutions, specifically designed for .NET AI development content. This pipeline supports adding, updating, and deleting documents with MongoDB storage, MarkItDown conversion, and OpenAI embeddings.

## Features

- **Document Management**: Add, update, and delete documents
- **Content Conversion**: Convert various input sources to Markdown using MarkItDown
- **Vector Embeddings**: Generate embeddings using OpenAI models
- **MongoDB Storage**: Store documents with metadata and vector embeddings
- **AI-Powered Tagging**: Intelligent framework categorization using OpenAI
- **Search Capabilities**: Vector similarity search with tag filtering
- **Command Line Interface**: Easy-to-use CLI for pipeline operations

## Prerequisites

- Python 3.8+
- MongoDB instance (local or cloud)
- OpenAI API key
- Virtual environment (recommended)

## Installation

1. **Clone or navigate to the project directory:**
   ```bash
   cd src/dataIngestion
   ```

2. **Activate virtual environment:**
   ```bash
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure the pipeline:**
   - Copy `env.example` to `.env` and update with your settings:
     ```bash
     cp env.example .env
     ```
   - Set your OpenAI API key
   - Configure MongoDB connection string

### Environment Variables

You can configure the pipeline using environment variables:

```bash
export OPENAI_API_KEY="your-openai-api-key"
export MONGODB_CONNECTION_STRING="mongodb://localhost:27017"
export MONGODB_DATABASE="rag_pipeline"
export MONGODB_COLLECTION="documents"
```

### Environment File

Copy `env.example` to `.env` and update with your settings:

```bash
cp env.example .env
```

Then edit `.env` with your configuration:

```env
# MongoDB Configuration
MONGODB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net
MONGODB_DATABASE=csharpAIBuddy
MONGODB_COLLECTION=documents

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Pipeline Settings
MAX_CONTENT_LENGTH=8192
BATCH_SIZE=10
```

## Usage

### Command Line Interface

The pipeline provides a comprehensive CLI for all operations:

#### Adding Documents

```bash
# Add a document with AI categorization (automatic)
python rag_data_pipeline.py add \
  --content "This is a tutorial about Semantic Kernel for .NET developers" \
  --source-url "https://example.com/tutorial"

# Add content with manual tags (disables AI categorization)
python rag_data_pipeline.py add \
  --content "$(cat document.txt)" \
  --source-path "/path/to/document.txt" \
  --source-type "text" \
  --tags "Semantic Kernel" "ML.NET"

# Add content with AI categorization disabled
python rag_data_pipeline.py add \
  --content "<html><body><h1>AI Tutorial</h1><p>Content here...</p></body></html>" \
  --source-type "html" \
  --no-ai-categorization
```

#### Updating Documents

```bash
# Update document content
python rag_data_pipeline.py update \
  --document-id "doc_20241201_143022_1234" \
  --content "Updated content here..."

# Update tags
python rag_data_pipeline.py update \
  --document-id "doc_20241201_143022_1234" \
  --tags "Semantic Kernel" "Semantic Kernel Agents"

# Update metadata
python rag_data_pipeline.py update \
  --document-id "doc_20241201_143022_1234" \
  --metadata '{"author": "John Doe", "version": "2.0"}'
```

#### Deleting Documents

```bash
python rag_data_pipeline.py delete --document-id "doc_20241201_143022_1234"
```

#### Retrieving Documents

```bash
# Get a specific document
python rag_data_pipeline.py get --document-id "doc_20241201_143022_1234"
```

#### Searching Documents

```bash
# Search by query
python rag_data_pipeline.py search \
  --query "How to use SemanticKernel with OpenAI" \
  --limit 5

# Search with tag filtering
python rag_data_pipeline.py search \
  --query "vector embeddings" \
  --tags "Semantic Kernel" "ML.NET" \
  --limit 10
```

#### Listing Documents

```bash
# List all documents
python rag_data_pipeline.py list --limit 20

# List documents by tags
python rag_data_pipeline.py list \
  --tags "Semantic Kernel" "ML.NET" \
  --limit 10
```

#### Getting Statistics

```bash
python rag_data_pipeline.py stats
```

### Programmatic Usage

You can also use the pipeline programmatically:

```python
from rag_data_pipeline import RAGDataPipeline
from config import Config
from dotnet_sdk_tags import categorize_with_ai

# Load configuration
config = Config.from_env()
pipeline = RAGDataPipeline(config)

# Add a document with AI categorization (automatic)
content = "This is a tutorial about using Semantic Kernel for .NET AI development."

doc_id = pipeline.add_document(
    content=content,
    source_url="https://example.com/tutorial",
    metadata={"author": "John Doe", "category": "AI Tutorial"}
    # AI categorization happens automatically when no tags are provided
)

# Search for documents
results = pipeline.search_documents(
    query="Semantic Kernel tutorial",
    tags=["Semantic Kernel"],
    limit=5
)

# Update a document
pipeline.update_document(
    document_id=doc_id,
    tags=["Semantic Kernel", "Semantic Kernel Agents"]
)
```

## AI-Powered Framework Categorization

The pipeline uses OpenAI to intelligently categorize content by .NET AI frameworks:

### Supported Frameworks
- **Microsoft.Extensions.AI**: Microsoft's AI extensions for .NET
- **ML.NET**: Microsoft's machine learning framework for .NET
- **AutoGen**: Microsoft's AutoGen framework for AI agents
- **Semantic Kernel**: Microsoft's AI orchestration library
- **Semantic Kernel Agents**: Semantic Kernel's agent framework
- **Semantic Kernel Process Framework**: Semantic Kernel's process orchestration
- **OpenAI SDK**: Official OpenAI SDK for .NET

### Automatic Categorization

The pipeline automatically categorizes content using AI:

```python
from dotnet_sdk_tags import categorize_with_ai

content = "Learn how to use Semantic Kernel with OpenAI embeddings for RAG applications"
tags = categorize_with_ai(content, openai_client)
# Returns: ['Semantic Kernel', 'OpenAI SDK']
```

### Semantic Kernel Family

Content mentioning Semantic Kernel sub-frameworks automatically gets both the specific tag and the parent "Semantic Kernel" tag:
- "Semantic Kernel Agents" → ["Semantic Kernel Agents", "Semantic Kernel"]
- "Semantic Kernel Process Framework" → ["Semantic Kernel Process Framework", "Semantic Kernel"]

## Document Structure

Each document in the pipeline contains:

```json
{
  "document_id": "doc_20241201_143022_1234",
  "source_url": "https://example.com/tutorial",
  "source_path": "/path/to/file.txt",
  "source_type": "text",
  "raw_content": "Original content...",
  "markdown_content": "# Converted Markdown\n\nContent...",
  "embeddings": [0.1, 0.2, 0.3, ...],
  "tags": ["Semantic Kernel"],
  "metadata": {
    "author": "John Doe",
    "category": "AI Tutorial",
    "version": "1.0"
  },
  "created_at": "2024-12-01T14:30:22Z",
  "updated_at": "2024-12-01T14:30:22Z"
}
```

## Vector Search

The pipeline supports semantic search using vector similarity:

- **Embedding Model**: Uses OpenAI's text-embedding-3-small by default
- **Similarity Calculation**: Cosine similarity between query and document embeddings
- **Filtering**: Combine vector search with tag-based filtering
- **Ranking**: Results ranked by similarity score

## Error Handling

The pipeline includes comprehensive error handling:

- **Configuration Validation**: Ensures all required settings are provided
- **API Error Handling**: Graceful handling of OpenAI API errors
- **MongoDB Connection**: Connection error handling and retry logic
- **Content Validation**: Validates content before processing
- **Tag Validation**: Validates tags against predefined categories

## Performance Considerations

- **Batch Processing**: Supports batch operations for bulk document processing
- **Content Length Limits**: Configurable maximum content length for embeddings
- **Connection Pooling**: Efficient MongoDB connection management
- **Indexing**: Automatic creation of MongoDB indexes for optimal performance

## Security

- **API Key Management**: Secure handling of OpenAI API keys
- **Environment Variables**: Support for environment-based configuration
- **Input Validation**: Validation of all input parameters
- **Error Logging**: Secure error logging without exposing sensitive data

## Troubleshooting

### Common Issues

1. **MongoDB Connection Error**
   - Verify MongoDB is running
   - Check connection string format
   - Ensure network connectivity

2. **OpenAI API Error**
   - Verify API key is valid
   - Check API quota and limits
   - Ensure proper internet connectivity

3. **MarkItDown Conversion Error**
   - Check input content format
   - Verify source type is supported
   - Review content for malformed HTML/URLs

### Logging

Enable debug logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Testing

The pipeline includes a comprehensive test suite for validating the AI categorization functionality:

### Running Tests

```bash
# Run all tests (mock only, no API key required)
python tests/run_tests.py

# Run with OpenAI evaluation (requires API key)
python tests/run_tests.py --openai

# Run specific test file
python tests/test_ai_categorization.py
```

### Test Coverage

- **Mock Tests**: Framework validation, categorization logic, error handling
- **OpenAI Evaluation Tests**: Real API integration for validation
- **Edge Cases**: Empty content, API errors, invalid tags

See `tests/README.md` for detailed testing documentation.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Run the test suite to ensure everything works
6. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:
- Check the troubleshooting section
- Review the error logs
- Open an issue in the repository 