def chunk_markdown(content, chunk_size):
    """
    Intelligently chunk markdown content while preserving structure.

    Args:
        content (str): The markdown content to chunk
        chunk_size (int): Maximum size in characters for each chunk

    Returns:
        list: List of markdown chunks as strings
    """

    def finalize_chunk(current_chunk, section_headers):
        """Helper to finalize a chunk with section headers."""
        if not current_chunk:
            return None

        chunk_content = []
        if section_headers:
            chunk_content.extend(section_headers)
        chunk_content.extend(current_chunk)
        return "\n".join(chunk_content)

    def add_chunk_if_not_empty(chunk):
        """Helper to add chunk to results if it's not empty."""
        if chunk and chunk.strip():
            chunks.append(chunk)

    chunks = []
    lines = content.split("\n")
    i = 0

    while i < len(lines):
        current_chunk = []
        current_size = 0
        section_headers = []

        # Collect section headers at the start
        while i < len(lines) and lines[i].strip().startswith("#"):
            header_line = lines[i]
            section_headers.append(header_line)
            current_size += len(header_line) + 1  # +1 for newline
            i += 1

        # Process content within this section
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Stop if we hit a new section header
            if stripped.startswith("#"):
                break

            # Handle code blocks - keep them intact
            if stripped.startswith("```"):
                code_block = [line]
                code_size = len(line) + 1
                i += 1

                # Collect the entire code block
                while i < len(lines):
                    code_line = lines[i]
                    code_block.append(code_line)
                    code_size += len(code_line) + 1
                    i += 1
                    if code_line.strip().startswith("```"):
                        break

                # Check if adding code block would exceed chunk size
                if current_size + code_size > chunk_size and current_chunk:
                    # Finalize current chunk and start new one
                    chunk = finalize_chunk(current_chunk, section_headers)
                    add_chunk_if_not_empty(chunk)
                    current_chunk = code_block
                    current_size = (
                        len("\n".join(section_headers)) + 1 + code_size
                        if section_headers
                        else code_size
                    )
                else:
                    current_chunk.extend(code_block)
                    current_size += code_size
                i += 1
                continue

            # Handle tables
            if "|" in line and stripped:
                table_lines = []
                table_header = None
                table_size = 0

                # Collect the entire table
                table_start = i
                while i < len(lines) and ("|" in lines[i] or not lines[i].strip()):
                    table_line = lines[i]
                    if "|" in table_line:
                        table_lines.append(table_line)
                        table_size += len(table_line) + 1

                        # Identify header (first line with |)
                        if table_header is None:
                            table_header = table_line
                        # Skip separator line detection for now - just keep first line as header
                    elif not table_line.strip():  # Empty line - might be end of table
                        # Look ahead to see if table continues
                        if i + 1 < len(lines) and "|" in lines[i + 1]:
                            table_lines.append(table_line)
                            table_size += len(table_line) + 1
                        else:
                            break
                    i += 1

                # Handle table chunking
                header_size = len(table_header) + 1 if table_header else 0

                if current_size + table_size <= chunk_size:
                    # Entire table fits in current chunk
                    current_chunk.extend(table_lines)
                    current_size += table_size
                else:
                    # Table needs to be split
                    if current_chunk:
                        # Finalize current chunk first
                        chunk = finalize_chunk(current_chunk, section_headers)
                        add_chunk_if_not_empty(chunk)
                        current_chunk = []
                        current_size = len("\n".join(section_headers)) + 1 if section_headers else 0

                    # Add table rows, creating new chunks as needed
                    table_chunk = []
                    table_chunk_size = 0
                    is_first_table_chunk = True

                    for table_line in table_lines:
                        line_size = len(table_line) + 1

                        if table_chunk_size + line_size > chunk_size and table_chunk:
                            # Finalize current table chunk
                            if is_first_table_chunk:
                                # First chunk gets the table as-is (no header duplication)
                                chunk = finalize_chunk(table_chunk, section_headers)
                                is_first_table_chunk = False
                            else:
                                # Subsequent chunks get header duplicated
                                if table_header:
                                    chunk_with_header = [table_header] + table_chunk
                                else:
                                    chunk_with_header = table_chunk
                                chunk = finalize_chunk(chunk_with_header, section_headers)

                            add_chunk_if_not_empty(chunk)

                            # Start new table chunk with current line
                            table_chunk = [table_line]
                            table_chunk_size = line_size
                        else:
                            table_chunk.append(table_line)
                            table_chunk_size += line_size

                    # Add remaining table content to current chunk
                    if table_chunk:
                        if is_first_table_chunk:
                            # First chunk gets the table as-is
                            current_chunk.extend(table_chunk)
                            current_size += table_chunk_size
                        else:
                            # Final chunk also needs header if it's not the first
                            if table_header:
                                chunk_with_header = [table_header] + table_chunk
                            else:
                                chunk_with_header = table_chunk
                            chunk = finalize_chunk(chunk_with_header, section_headers)
                            add_chunk_if_not_empty(chunk)

                continue

            # Handle lists - keep list items together
            if stripped.startswith(("-", "*", "+")) or (
                stripped and stripped[0].isdigit() and "." in stripped[:5]
            ):
                list_lines = []
                list_size = 0

                # Collect the entire list
                while i < len(lines):
                    list_line = lines[i]
                    list_stripped = list_line.strip()

                    # Check if this is a list item or continuation
                    if (
                        list_stripped.startswith(("-", "*", "+"))
                        or (
                            list_stripped
                            and list_stripped[0].isdigit()
                            and "." in list_stripped[:5]
                        )
                        or (
                            list_line.startswith("  ") or list_line.startswith("\t")
                        )  # Indented continuation
                        or not list_stripped
                    ):  # Empty line within list

                        list_lines.append(list_line)
                        list_size += len(list_line) + 1
                        i += 1

                        # If empty line, check if list continues
                        if not list_stripped and i < len(lines):
                            next_line = lines[i].strip()
                            if not (
                                next_line.startswith(("-", "*", "+"))
                                or (next_line and next_line[0].isdigit() and "." in next_line[:5])
                            ):
                                break
                    else:
                        break

                # Check if adding list would exceed chunk size
                if current_size + list_size > chunk_size and current_chunk:
                    chunk = finalize_chunk(current_chunk, section_headers)
                    add_chunk_if_not_empty(chunk)
                    current_chunk = list_lines
                    current_size = (
                        len("\n".join(section_headers)) + 1 + list_size
                        if section_headers
                        else list_size
                    )
                else:
                    current_chunk.extend(list_lines)
                    current_size += list_size

                continue

            # Handle paragraphs - collect until empty line or structural element
            paragraph_lines = []
            paragraph_size = 0

            while i < len(lines):
                para_line = lines[i]
                para_stripped = para_line.strip()

                # Stop at structural elements
                if (
                    para_stripped.startswith("#")
                    or para_stripped.startswith(("-", "*", "+"))
                    or (para_stripped and para_stripped[0].isdigit() and "." in para_stripped[:5])
                    or para_stripped.startswith("```")
                    or "|" in para_line
                ):
                    break

                paragraph_lines.append(para_line)
                paragraph_size += len(para_line) + 1
                i += 1

                # Stop at empty line (end of paragraph)
                if not para_stripped:
                    break

            # Check if adding paragraph would exceed chunk size
            if paragraph_lines:
                if current_size + paragraph_size > chunk_size and current_chunk:
                    chunk = finalize_chunk(current_chunk, section_headers)
                    add_chunk_if_not_empty(chunk)
                    current_chunk = paragraph_lines
                    current_size = (
                        len("\n".join(section_headers)) + 1 + paragraph_size
                        if section_headers
                        else paragraph_size
                    )
                else:
                    current_chunk.extend(paragraph_lines)
                    current_size += paragraph_size

        # Finalize any remaining content in current chunk
        if current_chunk:
            chunk = finalize_chunk(current_chunk, section_headers)
            add_chunk_if_not_empty(chunk)

    return chunks
