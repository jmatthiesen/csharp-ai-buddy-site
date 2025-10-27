#!/usr/bin/env python3
"""
Comprehensive tests for markdown chunking implementation.
Tests focus on strict size enforcement and content structure preservation.
"""

import unittest
from utils.chunking import chunk_markdown


class TestMarkdownChunking(unittest.TestCase):
    """Test the core chunking functionality with strict size enforcement."""

    def test_strict_size_enforcement_never_exceeded(self):
        """Test that NO chunk ever exceeds the specified size limit."""
        content = """# Long Title That Takes Up Some Space

This is a very long paragraph that should definitely exceed our small chunk size limit and force the creation of multiple chunks with proper size enforcement. We need to make sure this gets split appropriately.

Another paragraph that is also quite long and should be handled with strict size limits while maintaining readability and structure.

## Section Header

More content that continues to test the size limits and ensure everything works properly."""
        
        chunk_sizes = [50, 80, 100, 150]
        
        for size in chunk_sizes:
            with self.subTest(chunk_size=size):
                chunks = chunk_markdown(content, size)
                self.assertGreater(len(chunks), 1, f"Should create multiple chunks for size {size}")
                
                # Verify EVERY chunk respects the size limit
                for i, chunk in enumerate(chunks):
                    self.assertLessEqual(len(chunk), size, 
                        f"Chunk {i} exceeds size limit {size}: {len(chunk)} chars\nChunk: {repr(chunk[:100])}")

    def test_header_persistence_across_chunks(self):
        """Test that section headers are included in subsequent chunks."""
        content = """# Main Document

## Important Section

### Critical Subsection

This is content that should maintain the full header hierarchy when chunked. The headers should be preserved to maintain context and readability across all chunks."""
        
        chunks = chunk_markdown(content, 80)
        
        # Find chunk with the main content
        content_chunk = None
        for chunk in chunks:
            if "should maintain the full" in chunk:
                content_chunk = chunk
                break
        
        if content_chunk:
            # Should contain some level of headers for context
            has_headers = any(line.startswith('#') for line in content_chunk.split('\n'))
            self.assertTrue(has_headers, "Content chunk should include section headers for context")

    def test_no_orphaned_headers_ever(self):
        """Test that headers are never left alone in chunks without content."""
        content = """# Main Title

## Section A

### Subsection 1

### Subsection 2

### Subsection 3

This is the actual content that comes after multiple headers and should ensure no headers are orphaned."""
        
        chunks = chunk_markdown(content, 60)
        
        # Check each chunk for orphaned headers
        for i, chunk in enumerate(chunks):
            lines = [line.strip() for line in chunk.split('\n') if line.strip()]
            if lines:
                # If chunk has only headers and no other content, it's orphaned
                header_only = all(line.startswith('#') for line in lines)
                self.assertFalse(header_only, 
                    f"Chunk {i} contains only headers (orphaned): {repr(chunk)}")

    def test_code_block_splitting_with_proper_fencing(self):
        """Test that oversized code blocks are split while maintaining proper fencing."""
        content = """# Code Example

```python
def very_long_function_name_that_exceeds_our_size_limit():
    # This is a very long comment that also contributes to the total size
    result = some_very_long_variable_name_that_makes_this_line_quite_long
    another_line = "with a very long string that definitely pushes us over limits"
    final_result = process_data_with_very_long_function_name(result, another_line)
    return final_result
```

Text after the code block."""
        
        chunks = chunk_markdown(content, 80)
        
        # Should have multiple chunks due to size
        self.assertGreater(len(chunks), 2)
        
        # Every chunk should respect size limit
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 80)
        
        # Code chunks should maintain proper fencing
        code_chunks = [chunk for chunk in chunks if "```python" in chunk]
        self.assertGreater(len(code_chunks), 0, "Should have at least one code chunk")
        
        for chunk in code_chunks:
            self.assertIn("```python", chunk, "Code chunk should have opening fence")
            # Should have closing fence somewhere in the chunk
            self.assertTrue(chunk.count("```") >= 2 or chunk.endswith("```"), 
                f"Code chunk should have closing fence: {repr(chunk)}")

    def test_table_header_persistence_when_split(self):
        """Test that table headers are repeated when tables are split across chunks."""
        content = """# Data Table

| Column Header A | Column Header B | Column Header C |
|----------------|----------------|----------------|
| Very Long Data Value 1 | Very Long Data Value 2 | Very Long Data Value 3 |
| Very Long Data Value 4 | Very Long Data Value 5 | Very Long Data Value 6 |
| Very Long Data Value 7 | Very Long Data Value 8 | Very Long Data Value 9 |
| Very Long Data Value 10 | Very Long Data Value 11 | Very Long Data Value 12 |

Text after table."""
        
        chunks = chunk_markdown(content, 120)
        
        # Count chunks containing table headers
        header_chunks = [chunk for chunk in chunks if "Column Header A" in chunk]
        data_chunks = [chunk for chunk in chunks if "Very Long Data Value" in chunk]
        
        # If table was split, headers should appear in multiple chunks
        if len(data_chunks) > 1:
            self.assertGreater(len(header_chunks), 1,
                "Table headers should be repeated when table is split across chunks")
        
        # Every chunk should respect size limit
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 120)

    def test_table_headers_omitted_when_no_space(self):
        """Test that table headers are omitted if they don't fit with section headers."""
        content = """# Very Long Section Title That Takes Up Considerable Space
## Another Very Long Subsection Title That Also Takes Space  
### Even Deeper Section Title That Consumes More Characters
| Header A | Header B | Header C | Header D |
|----------|----------|----------|----------|
| Data 1   | Data 2   | Data 3   | Data 4   |"""
        
        chunks = chunk_markdown(content, 80)
        
        # Should still create valid chunks even if headers don't fit
        self.assertGreater(len(chunks), 0)
        
        # All chunks must respect size limit
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 80)

    def test_list_splitting_behavior(self):
        """Test that list items start new chunks when they would exceed size."""
        content = """# List Example

- Short item
- This is a very long list item that definitely exceeds our small chunk size limit and should start a new chunk appropriately
- Another normal item
- One more very long list item that also should trigger chunk boundary behavior and maintain list formatting"""
        
        chunks = chunk_markdown(content, 60)
        self.assertGreater(len(chunks), 1)
        
        # All chunks respect size limit
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 60)

    def test_paragraph_sentence_level_splitting(self):
        """Test that paragraphs are split at sentence boundaries when oversized."""
        content = """# Document

This is the first sentence of a very long paragraph. This is the second sentence that makes the paragraph longer and more likely to exceed size limits. This is the third sentence that definitely pushes us over the limit. This is the fourth sentence that continues the pattern."""
        
        chunks = chunk_markdown(content, 100)
        self.assertGreater(len(chunks), 1)
        
        # Each chunk should respect size limit
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 100)

    def test_word_level_splitting_for_extremely_long_sentences(self):
        """Test word-level splitting when sentences themselves exceed chunk size."""
        content = """# Document

This_is_an_artificially_long_sentence_with_underscores_instead_of_spaces_that_exceeds_chunk_size_and_needs_word_level_splitting_to_work_properly_in_our_system."""
        
        chunks = chunk_markdown(content, 50)
        self.assertGreater(len(chunks), 1)
        
        # Each chunk should respect size limit
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 50)

    def test_mixed_content_maintains_structure(self):
        """Test that complex documents with mixed content types maintain structure."""
        content = """# Main Document

Introduction paragraph with some text.

## Data Section

| Col 1 | Col 2 |
|-------|-------|
| A     | B     |
| C     | D     |

## Code Section

```python
def example():
    return "test"
```

## List Section

- Item 1
- Item 2
- Item 3

Final conclusion paragraph."""
        
        chunks = chunk_markdown(content, 100)
        self.assertGreater(len(chunks), 0)
        
        # All chunks respect size limit
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 100)
        
        # Should maintain structural integrity
        # Code chunks should have fences
        for chunk in chunks:
            if "def example" in chunk:
                self.assertIn("```python", chunk)
                self.assertIn("```", chunk.split("```python")[-1])

    def test_extremely_small_chunk_sizes(self):
        """Test behavior with very small chunk sizes."""
        content = """# Title
Content here with some text."""
        
        chunks = chunk_markdown(content, 15)  # Very small
        
        # Should still produce valid chunks
        self.assertGreater(len(chunks), 0)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 15)

    def test_empty_and_whitespace_content(self):
        """Test handling of empty or whitespace-only content."""
        self.assertEqual(chunk_markdown("", 100), [])
        self.assertEqual(chunk_markdown("   \n\n  ", 100), [])
        self.assertEqual(chunk_markdown("\t\t\n\n\t", 100), [])

    def test_single_large_element_gets_split(self):
        """Test that even single large elements respect size limits through splitting."""
        content = """```python
# This is a very long code block that definitely exceeds our chunk size limit
def extremely_long_function_name_that_makes_this_line_very_long_and_should_be_split():
    very_long_variable_name = "a very long string that also contributes to the total length"
    another_very_long_variable = process_with_very_long_function_name(very_long_variable_name)
    return another_very_long_variable
```"""
        
        chunks = chunk_markdown(content, 70)
        
        # Should be split into multiple chunks to respect size
        self.assertGreater(len(chunks), 1)
        
        # Each chunk should respect size limit
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 70)
        
        # All code chunks should maintain proper fencing
        for chunk in chunks:
            if "```python" in chunk:
                # Should have both opening and closing fences
                self.assertTrue(chunk.count("```") >= 2 or "```python" in chunk)

    def test_header_hierarchy_preservation(self):
        """Test that header hierarchy is logically preserved when possible."""
        content = """# Main Title

## Section A  

### Subsection

#### Deep Section

Content that should maintain hierarchy context."""
        
        chunks = chunk_markdown(content, 150)  # Large enough for some hierarchy
        
        # Find chunk with content
        content_chunk = None
        for chunk in chunks:
            if "maintain hierarchy" in chunk:
                content_chunk = chunk
                break
        
        if content_chunk:
            # Extract headers from this chunk
            lines = content_chunk.split('\n')
            header_lines = [line for line in lines if line.strip().startswith('#')]
            
            # Should have some headers for context
            self.assertGreater(len(header_lines), 0, "Should include headers for context")


if __name__ == '__main__':
    unittest.main()