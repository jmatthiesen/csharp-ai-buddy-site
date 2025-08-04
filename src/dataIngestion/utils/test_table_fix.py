#!/usr/bin/env python3
"""
Simple test to verify the table header duplication bug fix.
"""

from chunking import chunk_markdown

def test_table_header_fix():
    # Test content with a table that needs to be split
    content = """# Section
Some text before the table.

| Header 1 | Header 2 | Header 3 |
|----------|----------|----------|
| Row 1    | Data A   | Value X  |
| Row 2    | Data B   | Value Y  |
| Row 3    | Data C   | Value Z  |
| Row 4    | Data D   | Value W  |

Text after the table.
"""

    print("Original content:")
    print(content)
    print("\n" + "="*60)
    
    # Use a small chunk size to force table splitting
    chunks = chunk_markdown(content, 120)
    
    print(f"Number of chunks created: {len(chunks)}")
    print("\n" + "="*60)
    
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i} (length: {len(chunk)}):")
        print("-" * 40)
        print(chunk)
        
        # Check for header duplication in first table chunk
        if "Header 1" in chunk and "Row 1" in chunk:
            header_count = chunk.count("Header 1")
            print(f"\n>>> VERIFICATION: Header appears {header_count} time(s) in this chunk")
            if header_count == 1:
                print("✅ PASS: Header appears only once (no duplication)")
            else:
                print("❌ FAIL: Header is duplicated!")
        elif "Header 1" in chunk and "Row" in chunk:
            print("\n>>> VERIFICATION: This is a subsequent table chunk with duplicated header")
            print("✅ EXPECTED: Header duplication is correct for continuation chunks")

if __name__ == "__main__":
    test_table_header_fix()
