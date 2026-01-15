"""
Anchor Generator - Creates stable, hash-based IDs for content sections.

Why this matters: When I cite "paragraph 3", that reference needs to survive
document updates, re-chunking, and format changes. Hash-based anchors provide
stable references that don't break when content is reorganized.

The anchor ID format: anchor-{slug}-{hash8}
- slug: human-readable portion from the section title
- hash8: first 8 chars of SHA256 for uniqueness
"""

import hashlib
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Anchor:
    """A stable reference point in the document."""
    id: str
    line_start: int
    line_end: int
    type: str  # section, paragraph, list, table, code
    title: Optional[str] = None
    content_hash: Optional[str] = None  # Hash of the section content


class AnchorGenerator:
    """
    Generates stable, hash-based anchors for markdown content.
    
    Anchors are created for:
    - Headers (sections)
    - Paragraphs (if requested)
    - Code blocks
    - Tables
    - Lists
    """
    
    def __init__(self, include_paragraphs: bool = False):
        """
        Initialize the anchor generator.
        
        Args:
            include_paragraphs: If True, generate anchors for individual
                               paragraphs, not just sections. This creates
                               more granular citations but more anchors.
        """
        self.include_paragraphs = include_paragraphs
    
    def generate(self, markdown: str) -> dict[str, dict]:
        """
        Generate anchors for all significant content blocks.
        
        Args:
            markdown: Clean markdown content
            
        Returns:
            Dictionary mapping anchor IDs to anchor metadata
        """
        anchors = {}
        lines = markdown.split('\n')
        
        # Track current section for nesting
        current_section: Optional[dict] = None
        section_stack: list[dict] = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            # Check for headers (sections)
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if header_match:
                # Close previous section at same or higher level
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                
                # Find where this section ends
                section_end = self._find_section_end(lines, i, level)
                
                # Generate anchor
                anchor_id = self._generate_anchor_id(title, i, "section")
                section_content = '\n'.join(lines[i:section_end + 1])
                
                anchors[anchor_id] = {
                    "line_start": i,
                    "line_end": section_end,
                    "type": "section",
                    "title": title,
                    "level": level,
                    "content_hash": self._hash_content(section_content)[:16]
                }
                
                i += 1
                continue
            
            # Check for code blocks
            if line.startswith('```'):
                code_end = self._find_code_block_end(lines, i)
                if code_end > i:
                    lang = line[3:].strip() or "code"
                    anchor_id = self._generate_anchor_id(f"code-{lang}", i, "code")
                    code_content = '\n'.join(lines[i:code_end + 1])
                    
                    anchors[anchor_id] = {
                        "line_start": i,
                        "line_end": code_end,
                        "type": "code",
                        "title": f"Code block ({lang})",
                        "content_hash": self._hash_content(code_content)[:16]
                    }
                    
                    i = code_end + 1
                    continue
            
            # Check for tables
            if '|' in line and i + 1 < len(lines) and re.match(r'^[\s|:-]+$', lines[i + 1]):
                table_end = self._find_table_end(lines, i)
                anchor_id = self._generate_anchor_id("table", i, "table")
                table_content = '\n'.join(lines[i:table_end + 1])
                
                anchors[anchor_id] = {
                    "line_start": i,
                    "line_end": table_end,
                    "type": "table",
                    "title": "Table",
                    "content_hash": self._hash_content(table_content)[:16]
                }
                
                i = table_end + 1
                continue
            
            # Check for lists (only if include_paragraphs)
            if self.include_paragraphs and re.match(r'^[\s]*[-*+]\s', line):
                list_end = self._find_list_end(lines, i)
                anchor_id = self._generate_anchor_id("list", i, "list")
                list_content = '\n'.join(lines[i:list_end + 1])
                
                anchors[anchor_id] = {
                    "line_start": i,
                    "line_end": list_end,
                    "type": "list",
                    "title": "List",
                    "content_hash": self._hash_content(list_content)[:16]
                }
                
                i = list_end + 1
                continue
            
            # Check for paragraphs (only if include_paragraphs)
            if self.include_paragraphs and line.strip() and not line.startswith('#'):
                para_end = self._find_paragraph_end(lines, i)
                if para_end > i:  # Multi-line paragraph
                    para_content = '\n'.join(lines[i:para_end + 1])
                    # Only anchor substantial paragraphs
                    if len(para_content) > 100:
                        anchor_id = self._generate_anchor_id("para", i, "paragraph")
                        
                        anchors[anchor_id] = {
                            "line_start": i,
                            "line_end": para_end,
                            "type": "paragraph",
                            "title": para_content[:50] + "...",
                            "content_hash": self._hash_content(para_content)[:16]
                        }
                
                i = para_end + 1
                continue
            
            i += 1
        
        return anchors
    
    def _generate_anchor_id(self, title: str, line_num: int, anchor_type: str) -> str:
        """
        Generate a stable, unique anchor ID.
        
        Format: anchor-{slug}-{hash8}
        """
        # Create slug from title
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower())
        slug = slug.strip('-')[:20]
        
        # Create hash for uniqueness
        content = f"{title}:{line_num}:{anchor_type}"
        hash_prefix = hashlib.sha256(content.encode()).hexdigest()[:8]
        
        return f"anchor-{slug}-{hash_prefix}"
    
    def _hash_content(self, content: str) -> str:
        """Generate SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()
    
    def _find_section_end(self, lines: list[str], start: int, level: int) -> int:
        """Find where a section ends (next header of same/higher level or EOF)."""
        for i in range(start + 1, len(lines)):
            header_match = re.match(r'^(#{1,6})\s+', lines[i])
            if header_match:
                next_level = len(header_match.group(1))
                if next_level <= level:
                    return i - 1
        return len(lines) - 1
    
    def _find_code_block_end(self, lines: list[str], start: int) -> int:
        """Find the closing ``` of a code block."""
        for i in range(start + 1, len(lines)):
            if lines[i].startswith('```'):
                return i
        return start  # Unclosed code block
    
    def _find_table_end(self, lines: list[str], start: int) -> int:
        """Find where a table ends."""
        for i in range(start + 1, len(lines)):
            if '|' not in lines[i]:
                return i - 1
        return len(lines) - 1
    
    def _find_list_end(self, lines: list[str], start: int) -> int:
        """Find where a list ends."""
        for i in range(start + 1, len(lines)):
            line = lines[i]
            # List continues if line is list item or indented continuation
            if not (re.match(r'^[\s]*[-*+]\s', line) or 
                    re.match(r'^[\s]{2,}', line) or
                    re.match(r'^[\s]*\d+\.\s', line)):
                if line.strip():  # Non-empty, non-list line
                    return i - 1
        return len(lines) - 1
    
    def _find_paragraph_end(self, lines: list[str], start: int) -> int:
        """Find where a paragraph ends (blank line or special element)."""
        for i in range(start + 1, len(lines)):
            line = lines[i]
            # Paragraph ends at blank line or special element
            if not line.strip():
                return i - 1
            if line.startswith('#') or line.startswith('```') or line.startswith('|'):
                return i - 1
            if re.match(r'^[\s]*[-*+]\s', line):
                return i - 1
        return len(lines) - 1


def inject_anchor_ids(markdown: str, anchors: dict[str, dict]) -> str:
    """
    Inject anchor IDs into markdown content as HTML spans.
    
    This allows the anchors to be referenced in the rendered output.
    
    Args:
        markdown: Original markdown content
        anchors: Dictionary of anchors from AnchorGenerator
        
    Returns:
        Markdown with injected anchor spans
    """
    lines = markdown.split('\n')
    
    # Sort anchors by line number (descending) to avoid offset issues
    sorted_anchors = sorted(
        anchors.items(),
        key=lambda x: x[1]["line_start"],
        reverse=True
    )
    
    for anchor_id, anchor_data in sorted_anchors:
        line_num = anchor_data["line_start"]
        if 0 <= line_num < len(lines):
            # Inject anchor span at the start of the line
            lines[line_num] = f'<span id="{anchor_id}"></span>{lines[line_num]}'
    
    return '\n'.join(lines)
