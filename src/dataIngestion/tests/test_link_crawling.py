#!/usr/bin/env python3
"""
Unit tests for link crawling functionality.
Tests link extraction, pipeline integration, and CLI crawling features.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone
from bson import ObjectId

from dataIngestion.document_pipeline import DocumentPipeline
from pipeline_types import RawDocument, ProcessingContext, Chunk
from cli import RAGDataPipelineCLI
from config import Config


class TestLinkExtraction(unittest.TestCase):
    """Test link extraction functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=Config)
        self.mock_config.openai_api_key = "test-key"
        self.mock_config.mongodb_connection_string = "mongodb://localhost:27017"
        self.mock_config.mongodb_database = "test_db"
        self.mock_config.mongodb_collection = "test_collection"
        self.mock_config.mongodb_chunks_collection = "test_chunks_collection"
        self.mock_config.embedding_model = "text-embedding-3-small"

    @patch("document_pipeline_v2.MongoClient")
    @patch("document_pipeline_v2.OpenAI")
    @patch("document_pipeline_v2.MarkItDown")
    def _create_mock_pipeline(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Create a mock pipeline for testing."""
        # Setup mocks
        mock_documents_collection = Mock()
        mock_chunks_collection = Mock()
        mock_db = MagicMock()

        def mock_getitem(key):
            if key == "test_collection":
                return mock_documents_collection
            elif key == "test_chunks_collection":
                return mock_chunks_collection
            return Mock()

        mock_db.__getitem__.side_effect = mock_getitem
        mock_mongo_client = MagicMock()
        mock_mongo_client.__getitem__.return_value = mock_db
        mock_mongo_client_class.return_value = mock_mongo_client

        pipeline = DocumentPipeline(self.mock_config)
        pipeline.documents_collection = mock_documents_collection
        pipeline.chunks_collection = mock_chunks_collection

        return pipeline

    def test_extract_links_from_markdown_basic(self):
        """Test basic markdown link extraction."""
        pipeline = self._create_mock_pipeline()

        markdown_content = """
# Test Document

Here are some links:
- [User Guide](./guide.html)
- [API Reference](https://example.com/docs/api.md)
- [External Link](https://other.com/page)
- [Same Domain Deep](https://example.com/docs/tutorials/basic.html)
"""
        base_url = "https://example.com/docs/intro.html"

        links = pipeline.extract_links_from_markdown(markdown_content, base_url)

        # Should extract links that are same domain and same/deeper path
        self.assertEqual(len(links), 3)

        # Check that the right links were extracted
        urls = [link["url"] for link in links]
        self.assertIn("https://example.com/docs/guide.html", urls)
        self.assertIn("https://example.com/docs/api.md", urls)
        self.assertIn("https://example.com/docs/tutorials/basic.html", urls)

        # Check that external domain was filtered out
        self.assertNotIn("https://other.com/page", urls)

    def test_extract_links_from_markdown_relative_paths(self):
        """Test extraction of relative path links."""
        pipeline = self._create_mock_pipeline()

        markdown_content = """
[Relative link](./subpage.html)
[Parent link](../overview.md)
[Deep relative](./tutorials/advanced.html)
[Absolute path](/docs/reference.html)
"""
        base_url = "https://example.com/docs/intro.html"

        links = pipeline.extract_links_from_markdown(markdown_content, base_url)

        urls = [link["url"] for link in links]

        # Check relative links are converted to absolute
        self.assertIn("https://example.com/docs/subpage.html", urls)
        self.assertIn("https://example.com/docs/tutorials/advanced.html", urls)
        self.assertIn("https://example.com/docs/reference.html", urls)

    def test_extract_links_path_filtering(self):
        """Test that path filtering works correctly."""
        pipeline = self._create_mock_pipeline()

        markdown_content = """
[Same path](./page.html)
[Deeper path](./guides/page.html)
[Up directory](../other/page.html)
[Root level](https://example.com/other/page.html)
"""
        base_url = "https://example.com/docs/intro.html"

        links = pipeline.extract_links_from_markdown(markdown_content, base_url)

        urls = [link["url"] for link in links]

        # Should include same and deeper paths only
        self.assertIn("https://example.com/docs/page.html", urls)
        self.assertIn("https://example.com/docs/guides/page.html", urls)

        # Should exclude paths that go up the directory tree
        self.assertNotIn("https://example.com/other/page.html", urls)

    def test_extract_links_file_type_filtering(self):
        """Test that only valid file types are extracted."""
        pipeline = self._create_mock_pipeline()

        markdown_content = """
[HTML file](./page.html)
[Markdown file](./doc.md)
[Page without extension](./tutorials/)
[Image file](./image.png)
[PDF file](./document.pdf)
[JS file](./script.js)
"""
        base_url = "https://example.com/docs/intro.html"

        links = pipeline.extract_links_from_markdown(markdown_content, base_url)

        urls = [link["url"] for link in links]

        # Should include valid content types
        self.assertIn("https://example.com/docs/page.html", urls)
        self.assertIn("https://example.com/docs/doc.md", urls)
        self.assertIn("https://example.com/docs/tutorials/", urls)

        # Should exclude other file types
        self.assertNotIn("https://example.com/docs/image.png", urls)
        self.assertNotIn("https://example.com/docs/document.pdf", urls)
        self.assertNotIn("https://example.com/docs/script.js", urls)

    def test_extract_links_duplicate_removal(self):
        """Test that duplicate links are removed."""
        pipeline = self._create_mock_pipeline()

        markdown_content = """
[First reference](./guide.html)
[Second reference](./guide.html)
[Absolute reference](https://example.com/docs/guide.html)
"""
        base_url = "https://example.com/docs/intro.html"

        links = pipeline.extract_links_from_markdown(markdown_content, base_url)

        # Should only have one instance of the guide.html link
        urls = [link["url"] for link in links]
        guide_count = urls.count("https://example.com/docs/guide.html")
        self.assertEqual(guide_count, 1)

    def test_extract_links_with_titles(self):
        """Test extraction of links with titles."""
        pipeline = self._create_mock_pipeline()

        markdown_content = """
[User Guide](./guide.html "Complete user guide")
[API Docs](./api.md "API documentation")
[Simple Link](./simple.html)
"""
        base_url = "https://example.com/docs/intro.html"

        links = pipeline.extract_links_from_markdown(markdown_content, base_url)

        self.assertEqual(len(links), 3)

        # Check titles are preserved
        for link in links:
            if "guide.html" in link["url"]:
                self.assertEqual(link["title"], "Complete user guide")
            elif "api.md" in link["url"]:
                self.assertEqual(link["title"], "API documentation")
            elif "simple.html" in link["url"]:
                self.assertEqual(link["title"], "")

    def test_extract_links_empty_content(self):
        """Test link extraction with empty content."""
        pipeline = self._create_mock_pipeline()

        links = pipeline.extract_links_from_markdown(
            "", "https://example.com/docs/intro.html"
        )
        self.assertEqual(len(links), 0)

        links = pipeline.extract_links_from_markdown(
            "# Just a title", "https://example.com/docs/intro.html"
        )
        self.assertEqual(len(links), 0)


class TestLinkExtractionPipelineStage(unittest.TestCase):
    """Test the link extraction pipeline stage."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=Config)
        self.mock_config.openai_api_key = "test-key"
        self.mock_config.mongodb_connection_string = "mongodb://localhost:27017"
        self.mock_config.mongodb_database = "test_db"
        self.mock_config.mongodb_collection = "test_collection"
        self.mock_config.mongodb_chunks_collection = "test_chunks_collection"
        self.mock_config.embedding_model = "text-embedding-3-small"

    @patch("document_pipeline_v2.MongoClient")
    @patch("document_pipeline_v2.OpenAI")
    @patch("document_pipeline_v2.MarkItDown")
    def test_stage_link_extraction_success(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Test successful link extraction stage."""
        # Setup pipeline
        mock_documents_collection = Mock()
        mock_chunks_collection = Mock()
        mock_db = MagicMock()

        def mock_getitem(key):
            if key == "test_collection":
                return mock_documents_collection
            elif key == "test_chunks_collection":
                return mock_chunks_collection
            return Mock()

        mock_db.__getitem__.side_effect = mock_getitem
        mock_mongo_client = MagicMock()
        mock_mongo_client.__getitem__.return_value = mock_db
        mock_mongo_client_class.return_value = mock_mongo_client

        pipeline = DocumentPipeline(self.mock_config)
        pipeline.documents_collection = mock_documents_collection
        pipeline.chunks_collection = mock_chunks_collection

        # Create test context
        raw_doc = RawDocument(
            content="test content",
            source_url="https://example.com/docs/intro.html",
            title="Test Document",
        )
        context = ProcessingContext(raw_document=raw_doc)
        context.markdown_content = """
# Test Document
[User Guide](./guide.html)
[API Reference](./api.md)
"""

        # Run the stage
        pipeline._stage_link_extraction(context)

        # Check results
        self.assertEqual(len(context.extracted_links), 2)
        self.assertEqual(context.processing_metadata["links_extracted"], 2)
        self.assertIn("link_extraction", context.stages_completed)
        self.assertEqual(len(context.errors), 0)

    @patch("document_pipeline_v2.MongoClient")
    @patch("document_pipeline_v2.OpenAI")
    @patch("document_pipeline_v2.MarkItDown")
    def test_stage_link_extraction_no_markdown(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Test link extraction stage with no markdown content."""
        # Setup pipeline
        mock_documents_collection = Mock()
        mock_chunks_collection = Mock()
        mock_db = MagicMock()

        def mock_getitem(key):
            if key == "test_collection":
                return mock_documents_collection
            elif key == "test_chunks_collection":
                return mock_chunks_collection
            return Mock()

        mock_db.__getitem__.side_effect = mock_getitem
        mock_mongo_client = MagicMock()
        mock_mongo_client.__getitem__.return_value = mock_db
        mock_mongo_client_class.return_value = mock_mongo_client

        pipeline = DocumentPipeline(self.mock_config)
        pipeline.documents_collection = mock_documents_collection
        pipeline.chunks_collection = mock_chunks_collection

        # Create test context without markdown content
        raw_doc = RawDocument(
            content="test content",
            source_url="https://example.com/docs/intro.html",
            title="Test Document",
        )
        context = ProcessingContext(raw_document=raw_doc)
        # markdown_content is None

        # Run the stage
        pipeline._stage_link_extraction(context)

        # Check results
        self.assertEqual(len(context.extracted_links), 0)
        self.assertEqual(len(context.warnings), 1)
        self.assertIn("No markdown content available", context.warnings[0])
        self.assertIn("link_extraction", context.stages_completed)


class TestPipelineIntegration(unittest.TestCase):
    """Test link extraction integration with the full pipeline."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = Mock(spec=Config)
        self.mock_config.openai_api_key = "test-key"
        self.mock_config.mongodb_connection_string = "mongodb://localhost:27017"
        self.mock_config.mongodb_database = "test_db"
        self.mock_config.mongodb_collection = "test_collection"
        self.mock_config.mongodb_chunks_collection = "test_chunks_collection"
        self.mock_config.embedding_model = "text-embedding-3-small"

    @patch("document_pipeline_v2.MongoClient")
    @patch("document_pipeline_v2.OpenAI")
    @patch("document_pipeline_v2.MarkItDown")
    def test_process_document_includes_link_extraction(
        self, mock_markitdown_class, mock_openai_class, mock_mongo_client_class
    ):
        """Test that process_document includes link extraction and returns context."""
        # Setup mocks
        mock_documents_collection = Mock()
        mock_chunks_collection = Mock()
        mock_chunks_collection.delete_many.return_value = Mock(deleted_count=0)
        mock_chunks_collection.insert_one.return_value = Mock()

        mock_db = MagicMock()

        def mock_getitem(key):
            if key == "test_collection":
                return mock_documents_collection
            elif key == "test_chunks_collection":
                return mock_chunks_collection
            return Mock()

        mock_db.__getitem__.side_effect = mock_getitem
        mock_mongo_client = MagicMock()
        mock_mongo_client.__getitem__.return_value = mock_db
        mock_mongo_client_class.return_value = mock_mongo_client

        # Mock MarkItDown
        mock_markitdown = Mock()
        mock_result = Mock()
        mock_result.markdown = """
# Test Document
[User Guide](./guide.html)
[API Reference](./api.md)
"""
        mock_markitdown.convert.return_value = mock_result
        mock_markitdown_class.return_value = mock_markitdown

        # Mock OpenAI
        mock_client = Mock()
        mock_embedding_response = Mock()
        mock_embedding_response.data = [Mock(embedding=[0.1, 0.2, 0.3])]
        mock_client.embeddings.create.return_value = mock_embedding_response

        mock_chat_response = Mock()
        mock_chat_response.choices = [Mock(message=Mock(content="Test summary"))]
        mock_client.chat.completions.create.return_value = mock_chat_response
        mock_openai_class.return_value = mock_client

        # Create pipeline
        pipeline = DocumentPipeline(self.mock_config)
        pipeline.documents_collection = mock_documents_collection
        pipeline.chunks_collection = mock_chunks_collection

        # Create test document
        raw_doc = RawDocument(
            content="<html><body><h1>Test</h1><a href='./guide.html'>Guide</a></body></html>",
            source_url="https://example.com/docs/intro.html",
            title="Test Document",
            content_type="html",
        )

        # Process document
        context = pipeline.process_document(raw_doc, use_ai_categorization=False)

        # Check that context is returned with link extraction results
        self.assertIsInstance(context, ProcessingContext)
        self.assertEqual(len(context.extracted_links), 2)
        self.assertIn("stored_chunk_ids", context.processing_metadata)
        self.assertIn("links_extracted", context.processing_metadata)
        self.assertEqual(context.processing_metadata["links_extracted"], 2)


class TestCLICrawlingFunctionality(unittest.TestCase):
    """Test CLI crawling functionality."""

    @patch("cli.Config")
    def setUp(self, mock_config_class):
        """Set up test fixtures."""
        self.mock_config = Mock()
        mock_config_class.load.return_value = self.mock_config

        self.cli = RAGDataPipelineCLI()

    @patch("cli.input")
    def test_prompt_user_for_link_selection_all(self, mock_input):
        """Test user selecting all links."""
        mock_input.return_value = "all"

        links = [
            {
                "url": "https://example.com/docs/guide.html",
                "text": "User Guide",
                "title": "",
            },
            {
                "url": "https://example.com/docs/api.md",
                "text": "API Reference",
                "title": "",
            },
        ]

        selected = self.cli._prompt_user_for_link_selection(links)

        self.assertEqual(len(selected), 2)
        self.assertEqual(selected, links)

    @patch("cli.input")
    def test_prompt_user_for_link_selection_specific(self, mock_input):
        """Test user selecting specific links."""
        mock_input.return_value = "1,3"

        links = [
            {
                "url": "https://example.com/docs/guide.html",
                "text": "User Guide",
                "title": "",
            },
            {
                "url": "https://example.com/docs/api.md",
                "text": "API Reference",
                "title": "",
            },
            {
                "url": "https://example.com/docs/tutorial.html",
                "text": "Tutorial",
                "title": "",
            },
        ]

        selected = self.cli._prompt_user_for_link_selection(links)

        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[0]["text"], "User Guide")
        self.assertEqual(selected[1]["text"], "Tutorial")

    @patch("cli.input")
    def test_prompt_user_for_link_selection_none(self, mock_input):
        """Test user selecting no links."""
        mock_input.return_value = "none"

        links = [
            {
                "url": "https://example.com/docs/guide.html",
                "text": "User Guide",
                "title": "",
            },
        ]

        selected = self.cli._prompt_user_for_link_selection(links)

        self.assertEqual(len(selected), 0)

    @patch("cli.input")
    def test_prompt_user_for_link_selection_stop(self, mock_input):
        """Test user stopping crawling."""
        mock_input.return_value = "stop"

        links = [
            {
                "url": "https://example.com/docs/guide.html",
                "text": "User Guide",
                "title": "",
            },
        ]

        selected = self.cli._prompt_user_for_link_selection(links)

        self.assertEqual(len(selected), 0)

    @patch("cli.input")
    def test_prompt_user_for_link_selection_invalid_then_valid(self, mock_input):
        """Test user entering invalid input then valid input."""
        mock_input.side_effect = ["invalid", "1"]

        links = [
            {
                "url": "https://example.com/docs/guide.html",
                "text": "User Guide",
                "title": "",
            },
        ]

        selected = self.cli._prompt_user_for_link_selection(links)

        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0]["text"], "User Guide")

        # Check that input was called twice
        self.assertEqual(mock_input.call_count, 2)

    def test_add_document_from_url_crawl_prevention_duplicate(self):
        """Test that duplicate URLs are not processed."""
        # Mock the web retriever and pipeline
        self.cli.web_retriever = Mock()
        self.cli.pipeline = Mock()

        processed_urls = {"https://example.com/docs/intro.html"}

        result = self.cli.add_document_from_url(
            source_url="https://example.com/docs/intro.html",
            crawl_links=True,
            processed_urls=processed_urls,
        )

        # Should return None and not process
        self.assertIsNone(result)
        self.cli.web_retriever.fetch.assert_not_called()
        self.cli.pipeline.process_document.assert_not_called()


if __name__ == "__main__":
    unittest.main()
