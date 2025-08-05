def chunk_markdown(content, chunk_size):
    """
    Intelligently chunk markdown content while preserving structure.
    
    Args:
        content (str): The markdown content to chunk
        chunk_size (int): Maximum size in characters for each chunk
    
    Returns:
        list: List of markdown chunks as strings
    """
    if not content or not content.strip():
        return []
    
    lines = content.split('\n')
    chunks = []
    current_chunk = []
    current_size = 0
    section_headers = []  # Stack of current section hierarchy
    
    i = 0
    while i < len(lines):
        line = lines[i]
        line_type, content_block, next_i = identify_and_collect_content(lines, i)
        
        if line_type == 'header':
            # Update section headers stack
            header_level = line.count('#')
            
            # Remove headers at same or deeper level
            section_headers = [h for h in section_headers if h.count('#') < header_level]
            section_headers.append(line)
            
            # Check if adding header would exceed chunk size
            if current_size + len(line) + 1 > chunk_size and current_chunk:
                finalize_chunk(chunks, current_chunk)
                current_chunk = []
                current_size = 0
            
            # Add only the most recent header if starting new chunk (not the current one being processed)
            if not current_chunk and len(section_headers) > 1:
                last_header = section_headers[-2]  # Previous header (not current one)
                if len(last_header) + 1 <= chunk_size:
                    current_chunk.append(last_header)
                    current_size = len(last_header) + 1
            
            # Add current header if it fits
            if current_size + len(line) + 1 <= chunk_size:
                current_chunk.append(line)
                current_size += len(line) + 1
            else:
                # Header alone exceeds size - finalize current and start new
                if current_chunk:
                    finalize_chunk(chunks, current_chunk)
                current_chunk = [line]
                current_size = len(line) + 1
            
        elif line_type == 'table':
            process_table(content_block, section_headers, chunks, 
                                        current_chunk, current_size, chunk_size)
            current_chunk = []
            current_size = 0
        
        elif line_type == 'code_block':
            current_chunk, current_size = process_code_block(
                content_block, section_headers, chunks, current_chunk, current_size, chunk_size)
        
        elif line_type == 'list':
            current_chunk, current_size = process_list(
                content_block, section_headers, chunks, current_chunk, current_size, chunk_size)
        
        elif line_type == 'paragraph':
            current_chunk, current_size = process_paragraph(
                content_block, section_headers, chunks, current_chunk, current_size, chunk_size)
        
        elif line_type == 'empty':
            if current_size + len(line) + 1 <= chunk_size:
                current_chunk.append(line)
                current_size += len(line) + 1
        
        i = next_i
    
    # Finalize any remaining content
    if current_chunk:
        finalize_chunk(chunks, current_chunk)
    
    return chunks


def process_code_block(content_block, section_headers, chunks, 
                                     current_chunk, current_size, chunk_size):
    """Process code block with size limit enforcement."""
    block_size = calculate_content_size(content_block)
    
    # Try to fit entire code block in current chunk
    if current_size + block_size <= chunk_size:
        current_chunk.extend(content_block)
        return current_chunk, current_size + block_size
    
    # Finalize current chunk if it has content
    if current_chunk:
        finalize_chunk(chunks, current_chunk)
    
    # Check if code block fits with headers in new chunk
    headers_size = calculate_headers_size_that_fit(section_headers, chunk_size)
    if headers_size + block_size <= chunk_size:
        chunk_content = get_headers_that_fit(section_headers, chunk_size) + content_block
        finalize_chunk(chunks, chunk_content)
        return [], 0
    
    # Code block is too large - split it
    opening_fence = content_block[0] if content_block[0].strip().startswith('```') else '```'
    lang = opening_fence[3:].strip() if len(opening_fence) > 3 else ''
    closing_fence = '```'
    
    # Start new chunk with headers and opening fence
    current_chunk = get_headers_that_fit(section_headers, chunk_size)
    current_chunk.append(opening_fence)
    current_size = calculate_content_size(current_chunk)
    
    # Add code lines, splitting as needed
    code_lines = content_block[1:-1] if len(content_block) > 2 else content_block[1:]
    
    for code_line in code_lines:
        if current_size + len(code_line) + 1 + len(closing_fence) + 1 > chunk_size:
            # Finalize current code chunk
            current_chunk.append(closing_fence)
            finalize_chunk(chunks, current_chunk)
            
            # Start new code chunk
            new_opening = f'```{lang}' if lang else '```'
            current_chunk = [new_opening, code_line]
            current_size = len(new_opening) + 1 + len(code_line) + 1
        else:
            current_chunk.append(code_line)
            current_size += len(code_line) + 1
    
    # Add closing fence
    if current_size + len(closing_fence) + 1 <= chunk_size:
        current_chunk.append(closing_fence)
        current_size += len(closing_fence) + 1
    else:
        # Close current chunk and start new one with just closing fence
        current_chunk.append(closing_fence)
        finalize_chunk(chunks, current_chunk)
        return [], 0
    
    return current_chunk, current_size


def process_table(table_lines, section_headers, chunks, 
                                current_chunk, current_size, chunk_size):
    """Process table with strict size limits and header persistence."""
    # Finalize current chunk if it has content
    if current_chunk:
        finalize_chunk(chunks, current_chunk)
    
    if not table_lines:
        return
    
    # Identify table header and separator
    table_header = table_lines[0]
    separator_line = None
    data_start_idx = 1
    
    # Check for separator line
    if (len(table_lines) > 1 and 
        all(c in '|-: ' for c in table_lines[1].strip())):
        separator_line = table_lines[1]
        data_start_idx = 2
    
    # Build header block
    header_block = [table_header]
    if separator_line:
        header_block.append(separator_line)
    
    # Start first table chunk with only most recent section header if it fits
    section_header_that_fits = get_headers_that_fit(section_headers, chunk_size - calculate_content_size(header_block))
    current_table_chunk = section_header_that_fits + header_block
    current_table_size = calculate_content_size(current_table_chunk)
    
    # If even the header doesn't fit, create chunk without section headers
    if current_table_size > chunk_size:
        current_table_chunk = header_block
        current_table_size = calculate_content_size(header_block)
    
    # Process data rows
    data_rows = table_lines[data_start_idx:]
    
    for row in data_rows:
        row_size = len(row) + 1
        
        if current_table_size + row_size > chunk_size:
            # Finalize current table chunk
            if len(current_table_chunk) > len(header_block):
                finalize_chunk(chunks, current_table_chunk)
            
            # Start new table chunk with most recent header if it fits
            section_header_for_new_chunk = get_headers_that_fit(section_headers, chunk_size - calculate_content_size(header_block) - len(row) - 1)
            new_chunk_with_headers = section_header_for_new_chunk + header_block + [row]
            new_size = calculate_content_size(new_chunk_with_headers)
            
            if new_size <= chunk_size:
                # New chunk with headers fits
                current_table_chunk = new_chunk_with_headers
                current_table_size = new_size
            else:
                # Headers + row doesn't fit, start without section headers
                current_table_chunk = header_block + [row]
                current_table_size = calculate_content_size(current_table_chunk)
        else:
            current_table_chunk.append(row)
            current_table_size += row_size
    
    # Finalize final table chunk
    if len(current_table_chunk) > len(header_block):
        finalize_chunk(chunks, current_table_chunk)


def process_list(list_lines, section_headers, chunks, 
                               current_chunk, current_size, chunk_size):
    """Process list with size limit enforcement."""
    for line in list_lines:
        line_size = len(line) + 1
        
        if current_size + line_size > chunk_size:
            # Finalize current chunk if it has content
            if current_chunk:
                finalize_chunk(chunks, current_chunk)
            
            # Start new chunk with headers and this list item
            headers_that_fit = get_headers_that_fit(section_headers, chunk_size - line_size)
            current_chunk = headers_that_fit + [line]
            current_size = calculate_content_size(current_chunk)
        else:
            current_chunk.append(line)
            current_size += line_size
    
    return current_chunk, current_size


def process_paragraph(para_lines, section_headers, chunks, 
                                    current_chunk, current_size, chunk_size):
    """Process paragraph with sentence and word-level splitting."""
    paragraph_text = '\n'.join(para_lines).strip()
    
    # Split into sentences
    sentences = split_into_sentences(paragraph_text)
    
    for sentence in sentences:
        sentence_size = len(sentence) + 1  # +1 for space/newline
        
        if current_size + sentence_size <= chunk_size:
            # Sentence fits in current chunk
            if current_chunk and not current_chunk[-1].endswith('\n'):
                current_chunk[-1] += ' ' + sentence
                current_size += sentence_size
            else:
                current_chunk.append(sentence)
                current_size += sentence_size
        else:
            # Sentence doesn't fit - finalize current chunk
            if current_chunk:
                finalize_chunk(chunks, current_chunk)
            
            # Try sentence with headers in new chunk
            headers_that_fit = get_headers_that_fit(section_headers, chunk_size)
            headers_size = calculate_content_size(headers_that_fit)
            
            if headers_size + sentence_size <= chunk_size:
                current_chunk = headers_that_fit + [sentence]
                current_size = headers_size + sentence_size
            else:
                # Sentence too large - split by words
                current_chunk, current_size = split_sentence_by_words(
                    sentence, headers_that_fit, chunks, chunk_size)
    
    return current_chunk, current_size


def split_sentence_by_words(sentence, headers, chunks, chunk_size):
    """Split long sentence by words."""
    words = sentence.split()
    
    current_chunk = headers[:]
    current_size = calculate_content_size(current_chunk)
    current_sentence = ""
    
    for word in words:
        word_with_space = (' ' + word) if current_sentence else word
        
        if current_size + len(word_with_space) > chunk_size:
            # Finalize current chunk
            if current_sentence:
                current_chunk.append(current_sentence)
            if current_chunk:
                finalize_chunk(chunks, current_chunk)
            
            # Start new chunk
            current_chunk = headers[:]
            current_size = calculate_content_size(current_chunk)
            current_sentence = word
            current_size += len(word)
        else:
            current_sentence += word_with_space
            current_size += len(word_with_space)
    
    # Add final sentence to chunk
    if current_sentence:
        current_chunk.append(current_sentence)
        current_size += len(current_sentence) + 1
    
    return current_chunk, current_size


def split_into_sentences(text):
    """Simple sentence splitting."""
    import re
    # Split on sentence endings, keeping the punctuation
    sentences = re.split(r'([.!?]+)', text)
    result = []
    
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i].strip()
        punctuation = sentences[i + 1] if i + 1 < len(sentences) else ''
        if sentence:
            result.append(sentence + punctuation)
    
    return result if result else [text]


def get_headers_that_fit(section_headers, max_size):
    """Get only the most recent header that fits within size limit."""
    if not section_headers:
        return []
    
    # Only use the most recent header
    last_header = section_headers[-1]
    if len(last_header) + 1 <= max_size:
        return [last_header]
    else:
        return []


def calculate_headers_size_that_fit(section_headers, max_size):
    """Calculate size of headers that fit within limit."""
    return calculate_content_size(get_headers_that_fit(section_headers, max_size))


def identify_and_collect_content(lines, start_index):
    """Identify content type and collect complete block."""
    if start_index >= len(lines):
        return 'end', [], start_index
    
    line = lines[start_index]
    stripped = line.strip()
    
    if stripped.startswith('#'):
        return 'header', [line], start_index + 1
    
    if not stripped:
        return 'empty', [line], start_index + 1
    
    if stripped.startswith('```'):
        return collect_code_block(lines, start_index)
    
    if '|' in line and stripped:
        return collect_table(lines, start_index)
    
    if (stripped.startswith(('-', '*', '+')) or 
        (stripped and stripped[0].isdigit() and '.' in stripped[:10])):
        return collect_list(lines, start_index)
    
    return collect_paragraph(lines, start_index)


def collect_code_block(lines, start_index):
    """Collect entire code block."""
    content = [lines[start_index]]
    i = start_index + 1
    
    while i < len(lines):
        content.append(lines[i])
        if lines[i].strip().startswith('```'):
            i += 1
            break
        i += 1
    
    return 'code_block', content, i


def collect_table(lines, start_index):
    """Collect entire table."""
    content = []
    i = start_index
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if '|' in line and stripped:
            content.append(line)
            i += 1
        elif not stripped and i + 1 < len(lines) and '|' in lines[i + 1]:
            content.append(line)
            i += 1
        else:
            break
    
    return 'table', content, i


def collect_list(lines, start_index):
    """Collect entire list."""
    content = []
    i = start_index
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        is_list_item = (stripped.startswith(('-', '*', '+')) or 
                       (stripped and stripped[0].isdigit() and '.' in stripped[:10]))
        
        is_continuation = (line.startswith('  ') or line.startswith('\t'))
        
        if is_list_item or is_continuation:
            content.append(line)
            i += 1
        elif not stripped:
            # Check if list continues
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if (next_line.startswith(('-', '*', '+')) or 
                    (next_line and next_line[0].isdigit() and '.' in next_line[:10])):
                    content.append(line)
                    i += 1
                else:
                    break
            else:
                break
        else:
            break
    
    return 'list', content, i


def collect_paragraph(lines, start_index):
    """Collect entire paragraph."""
    content = []
    i = start_index
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if (stripped.startswith('#') or 
            stripped.startswith(('-', '*', '+')) or
            (stripped and stripped[0].isdigit() and '.' in stripped[:10]) or
            stripped.startswith('```') or
            '|' in line):
            break
        
        content.append(line)
        i += 1
        
        if not stripped:
            break
    
    return 'paragraph', content, i


def calculate_content_size(content_lines):
    """Calculate total size of content lines."""
    return sum(len(line) + 1 for line in content_lines)


def finalize_chunk(chunks, chunk_content):
    """Add chunk to results if it has content."""
    if chunk_content:
        chunk_text = '\n'.join(chunk_content)
        if chunk_text.strip():
            chunks.append(chunk_text)