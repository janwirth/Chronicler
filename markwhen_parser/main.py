#!/usr/bin/env python3
"""
Markwhen Parser - Parse and write markwhen timeline files
Based on https://docs.markwhen.com/syntax/
"""

import re
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path


class MarkwhenEvent:
    """Represents a markwhen event"""
    
    def __init__(self, date_str: str, description: str, properties: Optional[Dict[str, Any]] = None):
        self.date_str = date_str  # Original date string (e.g., "2025-01-15T10:30:00" or "2025-01/2025-03")
        self.description = description
        self.properties = properties or {}
        self.tags = []
        self.links = []
        self.references = []
        self.photos = []
        self.content_lines = []  # Additional content lines (description, checkboxes, etc.)
    
    def __repr__(self):
        return f"MarkwhenEvent(date='{self.date_str}', desc='{self.description[:30]}...')"


class MarkwhenParser:
    """Parser for markwhen timeline files"""
    
    def __init__(self):
        # Regex patterns for markwhen syntax
        self.event_pattern = re.compile(
            r'^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}|[\d/]+(?:-\d{2,4})?(?:/\d{2,4})?):\s*(.+)$'
        )
        self.tag_pattern = re.compile(r'#(\w+)')
        self.link_pattern = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
        self.photo_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        self.reference_pattern = re.compile(r'@(\w+)')
        self.comment_pattern = re.compile(r'^\s*//.*$')
    
    def parse_frontmatter(self, lines: List[str]) -> Tuple[Dict[str, Any], int]:
        """
        Parse YAML frontmatter from markwhen file.
        Returns (frontmatter_dict, end_index)
        """
        frontmatter = {}
        end_idx = 0
        
        if not lines or lines[0].strip() != "---":
            return frontmatter, end_idx
        
        # Find closing ---
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == "---":
                end_idx = i + 1
                break
        
        # Parse YAML (simple key-value parsing)
        for line in lines[1:end_idx-1]:
            line = line.strip()
            if not line:
                continue
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                frontmatter[key] = value
        
        return frontmatter, end_idx
    
    def parse_event_line(self, line: str) -> Optional[MarkwhenEvent]:
        """
        Parse a single event line in markwhen format.
        Examples:
        - "2025-01-15T10:30:00: App Name"
        - "2025-01/2025-03: Project task"
        """
        line = line.strip()
        
        # Skip comments
        if self.comment_pattern.match(line):
            return None
        
        # Match event pattern: date: description
        match = self.event_pattern.match(line)
        if not match:
            return None
        
        date_str = match.group(1)
        description = match.group(2).strip()
        
        event = MarkwhenEvent(date_str, description)
        
        # Extract tags (include # prefix)
        event.tags = ['#' + tag for tag in self.tag_pattern.findall(description)]
        
        # Extract links
        for link_match in self.link_pattern.finditer(description):
            event.links.append({
                'text': link_match.group(1),
                'url': link_match.group(2)
            })
        
        # Extract photos
        for photo_match in self.photo_pattern.finditer(description):
            event.photos.append({
                'alt': photo_match.group(1),
                'url': photo_match.group(2)
            })
        
        # Extract references
        event.references = self.reference_pattern.findall(description)
        
        return event
    
    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a complete markwhen file.
        Returns dict with 'frontmatter' and 'events' keys.
        """
        if not file_path.exists():
            return {'frontmatter': {}, 'events': []}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Parse frontmatter
        frontmatter, start_idx = self.parse_frontmatter(lines)
        
        # Parse events
        events = []
        current_event = None
        
        for i, line in enumerate(lines[start_idx:], start_idx):
            line_stripped = line.strip()
            
            # Skip empty lines between events (but save current event first)
            if not line_stripped:
                if current_event:
                    events.append(current_event)
                    current_event = None
                continue
            
            # Try to parse as event line
            event = self.parse_event_line(line)
            if event:
                if current_event:
                    events.append(current_event)
                current_event = event
            elif current_event:
                # This is content for the current event
                # Check if it's a property (key: value)
                if ':' in line_stripped and not line_stripped.startswith('#'):
                    parts = line_stripped.split(':', 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip().strip('"').strip("'")
                        current_event.properties[key] = value
                else:
                    # Regular content line
                    current_event.content_lines.append(line.rstrip('\n'))
        
        # Add last event
        if current_event:
            events.append(current_event)
        
        return {
            'frontmatter': frontmatter,
            'events': events
        }
    
    def parse_last_event(self, file_path: Path) -> Optional[str]:
        """
        Parse the last event from a markwhen file and return the app name.
        This is a convenience method for the chronicler use case.
        """
        result = self.parse_file(file_path)
        
        if not result['events']:
            return None
        
        last_event = result['events'][-1]
        return last_event.description
    
    def write_frontmatter(self, frontmatter: Dict[str, Any]) -> str:
        """Generate frontmatter YAML string"""
        lines = ["---"]
        for key, value in frontmatter.items():
            lines.append(f"{key}: {value}")
        lines.append("---")
        lines.append("")
        return "\n".join(lines)
    
    def write_event(self, event: MarkwhenEvent) -> str:
        """Generate markwhen event string"""
        lines = [f"{event.date_str}: {event.description}"]
        
        # Add properties
        for key, value in event.properties.items():
            if isinstance(value, list):
                lines.append(f"  {key}: [{', '.join(str(v) for v in value)}]")
            elif isinstance(value, str) and (' ' in value or ':' in value):
                lines.append(f"  {key}: \"{value}\"")
            else:
                lines.append(f"  {key}: {value}")
        
        # Add content lines
        for content_line in event.content_lines:
            lines.append(content_line)
        
        lines.append("")  # Empty line after event
        return "\n".join(lines)
    
    def ensure_frontmatter(self, file_path: Path, title: Optional[str] = None, date: Optional[str] = None):
        """
        Ensure a markwhen file exists with frontmatter.
        If file doesn't exist, create it with frontmatter.
        If file exists but has no frontmatter, add it.
        """
        if not file_path.exists():
            frontmatter = {}
            if title:
                frontmatter['title'] = title
            if date:
                frontmatter['date'] = date
            else:
                frontmatter['date'] = datetime.now().strftime('%Y-%m-%d')
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.write_frontmatter(frontmatter))
            return
        
        # Check if frontmatter exists
        with open(file_path, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
        
        if first_line != "---":
            # No frontmatter, read existing content
            with open(file_path, 'r', encoding='utf-8') as f:
                existing_content = f.read()
            
            # Prepend frontmatter
            frontmatter = {}
            if title:
                frontmatter['title'] = title
            if date:
                frontmatter['date'] = date
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.write_frontmatter(frontmatter))
                f.write(existing_content)
    
    def append_event(self, file_path: Path, app_name: str, timestamp: datetime, typed_content: str = ""):
        """
        Append an event to a markwhen file, or append to last event if same app.
        This is a convenience method for the chronicler use case.
        """
        # Ensure file exists with frontmatter
        self.ensure_frontmatter(file_path)
        
        # Parse to get last event
        last_app = self.parse_last_event(file_path)
        
        # Format timestamp in markwhen format: YYYY-MM-DDTHH:MM:SS
        timestamp_str = timestamp.strftime('%Y-%m-%dT%H:%M:%S')
        
        with open(file_path, 'a', encoding='utf-8') as f:
            if last_app == app_name:
                # Append to existing entry
                if typed_content.strip():
                    f.write(typed_content)
            else:
                # Create new entry
                f.write(f"{timestamp_str}: {app_name}\n")
                if typed_content.strip():
                    f.write(f"{typed_content}\n")
                f.write("\n")


# Test functions
def test_parse_frontmatter():
    """Test frontmatter parsing"""
    parser = MarkwhenParser()
    
    lines = [
        "---",
        "title: Project plan",
        "timezone: America/New_York",
        "---",
        "",
        "2025-01-15T10:30:00: Test event"
    ]
    
    frontmatter, end_idx = parser.parse_frontmatter(lines)
    assert frontmatter['title'] == 'Project plan'
    assert frontmatter['timezone'] == 'America/New_York'
    assert end_idx == 4
    print("✓ test_parse_frontmatter passed")


def test_parse_event():
    """Test event parsing"""
    parser = MarkwhenParser()
    
    # Test ISO8601 format
    event = parser.parse_event_line("2025-01-15T10:30:00: App Name")
    assert event is not None
    assert event.date_str == "2025-01-15T10:30:00"
    assert event.description == "App Name"
    
    # Test with tags
    event = parser.parse_event_line("2025-01-15T10:30:00: Project task #Project1 #John")
    assert event is not None
    assert "#Project1" in event.tags
    assert "#John" in event.tags
    
    # Test with links
    event = parser.parse_event_line("2025-01-15T10:30:00: Check [this link](https://example.com)")
    assert event is not None
    assert len(event.links) == 1
    assert event.links[0]['url'] == "https://example.com"
    
    # Test comment
    event = parser.parse_event_line("// This is a comment")
    assert event is None
    
    print("✓ test_parse_event passed")


def test_parse_file():
    """Test full file parsing"""
    parser = MarkwhenParser()
    
    # Create a test file
    test_file = Path("/tmp/test_markwhen.md")
    content = """---
title: Test Timeline
date: 2025-01-15
---
2025-01-15T10:30:00: First App
  Some content here

2025-01-15T11:00:00: Second App #Work
  More content
  - [x] Task 1
  - [ ] Task 2
"""
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    result = parser.parse_file(test_file)
    
    assert result['frontmatter']['title'] == 'Test Timeline'
    assert len(result['events']) == 2
    assert result['events'][0].description == 'First App'
    assert result['events'][1].description == 'Second App #Work'
    assert len(result['events'][1].tags) == 1
    
    # Cleanup
    test_file.unlink()
    print("✓ test_parse_file passed")


def test_parse_last_event():
    """Test parsing last event"""
    parser = MarkwhenParser()
    
    test_file = Path("/tmp/test_markwhen2.md")
    content = """---
title: Test
---
2025-01-15T10:30:00: First App
2025-01-15T11:00:00: Second App
"""
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    last_app = parser.parse_last_event(test_file)
    assert last_app == "Second App"
    
    # Cleanup
    test_file.unlink()
    print("✓ test_parse_last_event passed")


def test_ensure_frontmatter():
    """Test ensuring frontmatter exists"""
    parser = MarkwhenParser()
    
    test_file = Path("/tmp/test_markwhen3.md")
    
    # Test creating new file
    parser.ensure_frontmatter(test_file, title="New Timeline")
    
    assert test_file.exists()
    with open(test_file, 'r', encoding='utf-8') as f:
        content = f.read()
        assert "title: New Timeline" in content
        assert "---" in content
    
    # Cleanup
    test_file.unlink()
    print("✓ test_ensure_frontmatter passed")


def test_append_event():
    """Test appending events"""
    parser = MarkwhenParser()
    
    test_file = Path("/tmp/test_markwhen4.md")
    
    # Create file with frontmatter
    parser.ensure_frontmatter(test_file, title="Test")
    
    # Append first event
    timestamp1 = datetime(2025, 1, 15, 10, 30, 0)
    parser.append_event(test_file, "App1", timestamp1, "typed content")
    
    # Append second event (different app)
    timestamp2 = datetime(2025, 1, 15, 11, 0, 0)
    parser.append_event(test_file, "App2", timestamp2, "more content")
    
    # Append to same app (should append to last event)
    timestamp3 = datetime(2025, 1, 15, 11, 5, 0)
    parser.append_event(test_file, "App2", timestamp3, "even more")
    
    # Verify
    result = parser.parse_file(test_file)
    assert len(result['events']) == 2
    assert result['events'][0].description == "App1"
    assert result['events'][1].description == "App2"
    
    # Cleanup
    test_file.unlink()
    print("✓ test_append_event passed")


def run_all_tests():
    """Run all tests"""
    print("Running markwhen parser tests...")
    print()
    
    try:
        test_parse_frontmatter()
        test_parse_event()
        test_parse_file()
        test_parse_last_event()
        test_ensure_frontmatter()
        test_append_event()
        
        print()
        print("All tests passed! ✓")
    except AssertionError as e:
        print(f"Test failed: {e}")
        raise
    except Exception as e:
        print(f"Error running tests: {e}")
        raise


if __name__ == "__main__":
    run_all_tests()

