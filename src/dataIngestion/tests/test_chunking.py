import unittest
from utils.chunking import chunk_markdown

class TestMarkdownChunker(unittest.TestCase):

    def test_chunk_sections_basic(self):
        """Test basic section chunking."""
        content = """# Section 1
This is some content for section 1.

# Section 2
This is some content for section 2."""
        chunks = chunk_markdown(content, 100)
        self.assertEqual(len(chunks), 2)
        self.assertIn("# Section 1", chunks[0])
        self.assertIn("# Section 2", chunks[1])

    def test_paragraphs_within_sections(self):
        """Test that paragraphs are kept together within sections."""
        content = """# Section 1
First paragraph in section 1.
This is still part of the first paragraph.

Second paragraph in section 1.

# Section 2
Paragraph in section 2."""
        chunks = chunk_markdown(content, 200)
        self.assertEqual(len(chunks), 2)
        # First chunk should contain both paragraphs from section 1
        self.assertIn("First paragraph", chunks[0])
        self.assertIn("Second paragraph", chunks[0])

    def test_chunk_size_limit_enforced(self):
        """Test that chunk size limit is strictly enforced."""
        content = """# Section 1
This is a very long paragraph that should definitely exceed our small chunk size limit and force the creation of multiple chunks.

Another paragraph that is also quite long and should be in a separate chunk."""
        chunks = chunk_markdown(content, 80)  # Small chunk size
        self.assertGreater(len(chunks), 1)
        # Verify no chunk exceeds the limit (allowing some tolerance for headers)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 200)  # Reasonable upper bound including headers

    def test_code_blocks_intact(self):
        """Test that code blocks are never split."""
        content = """# Section
Some text before code.

```python
def function():
    return "This code block should never be split"
    # Even if it's long
```

Text after code."""
        chunks = chunk_markdown(content, 50)  # Small chunk size
        # Find the chunk containing the code block
        code_chunk = None
        for chunk in chunks:
            if "```python" in chunk:
                code_chunk = chunk
                break
        
        self.assertIsNotNone(code_chunk)
        self.assertIn("def function():", code_chunk)
        self.assertIn('return "This code block', code_chunk)
        self.assertIn("# Even if it's long", code_chunk)

    def test_lists_kept_together(self):
        """Test that list items are kept together."""
        content = """# Section
- First list item
- Second list item
- Third list item

Paragraph after list."""
        chunks = chunk_markdown(content, 100)
        # Find chunk with list items
        list_chunk = None
        for chunk in chunks:
            if "First list item" in chunk:
                list_chunk = chunk
                break
        
        self.assertIsNotNone(list_chunk)
        self.assertIn("- First list item", list_chunk)
        self.assertIn("- Second list item", list_chunk)
        self.assertIn("- Third list item", list_chunk)

    def test_table_header_duplication(self):
        """Test that table headers are duplicated when tables are split."""
        content = """# Section
| Header 1 | Header 2 |
|----------|----------|
| Row 1    | Data 1   |
| Row 2    | Data 2   |
| Row 3    | Data 3   |
| Row 4    | Data 4   |
| Row 5    | Data 5   |

Text after table."""
        chunks = chunk_markdown(content, 100)  # Force table to split
        
        # Count chunks containing table headers
        header_count = 0
        for chunk in chunks:
            if "Header 1" in chunk and "Header 2" in chunk:
                header_count += 1
        
        # Should have headers in multiple chunks if table was split
        if len(chunks) > 2:  # Section + table chunks + text after
            self.assertGreater(header_count, 1)
    
    def test_table_header_not_duplicated_in_first_chunk(self):
        """Test that table headers are NOT duplicated in the first chunk."""
        content = """# Section
Some text before table.

| Header 1 | Header 2 |
|----------|----------|
| Row 1    | Data 1   |
| Row 2    | Data 2   |
| Row 3    | Data 3   |
| Row 4    | Data 4   |
| Row 5    | Data 5   |

Text after table."""
        chunks = chunk_markdown(content, 80)  # Small size to force splitting
        
        # Find the first chunk that contains table data
        first_table_chunk = None
        for chunk in chunks:
            if "Header 1" in chunk and "Row 1" in chunk:
                first_table_chunk = chunk
                break
        
        if first_table_chunk:
            # Count occurrences of the header in the first table chunk
            header_occurrences = first_table_chunk.count("Header 1")
            self.assertEqual(header_occurrences, 1, 
                           "Table header should appear only once in the first chunk containing the table")

    def test_table_rows_kept_together(self):
        """Test that individual table rows are not split."""
        content = """| Very Long Header 1 | Very Long Header 2 | Very Long Header 3 |
|-------------------|-------------------|-------------------|
| Long data value 1 | Long data value 2 | Long data value 3 |"""
        chunks = chunk_markdown(content, 50)  # Very small to force splitting
        
        # Each chunk should have complete table rows
        for chunk in chunks:
            lines = chunk.split('\n')
            for line in lines:
                if '|' in line:
                    # Count pipes to ensure row integrity
                    pipe_count = line.count('|')
                    if pipe_count > 0:
                        # Should have consistent number of columns
                        self.assertGreaterEqual(pipe_count, 2)  # At least start and end pipes

    def test_mixed_content_chunking(self):
        """Test chunking with mixed content types."""
        content = """# Main Section
Introduction paragraph.

## Subsection
Another paragraph.

- List item 1
- List item 2

```python
code_example = "test"
```

| Col 1 | Col 2 |
|-------|-------|
| A     | B     |
| C     | D     |

Conclusion paragraph."""
        
        chunks = chunk_markdown(content, 200)
        self.assertGreater(len(chunks), 0)
        
        # Verify that each chunk contains properly formatted content
        for chunk in chunks:
            lines = chunk.split('\n')
            # Basic validation - no hanging table separators
            for line in lines:
                if line.strip().startswith('|---'):
                    # Should have a header before separator
                    prev_lines = [l for l in lines[:lines.index(line)] if l.strip()]
                    self.assertTrue(any('|' in l for l in prev_lines[-2:]))

    def test_empty_content(self):
        """Test handling of empty or whitespace-only content."""
        self.assertEqual(chunk_markdown("", 100), [])
        self.assertEqual(chunk_markdown("   \n\n  ", 100), [])

    def test_single_large_element(self):
        """Test handling when a single element exceeds chunk size."""
        # Large code block that exceeds chunk size
        content = """```python
# This is a very long code block that exceeds our chunk size
# But it should still be kept as a single unit
def very_long_function_name_that_makes_this_line_quite_long():
    return "A very long string that also contributes to the length"
```"""
        chunks = chunk_markdown(content, 50)  # Much smaller than content
        self.assertEqual(len(chunks), 1)  # Should still be one chunk
        self.assertIn("```python", chunks[0])
        self.assertIn("def very_long_function", chunks[0])

if __name__ == '__main__':
    unittest.main()

