#!/usr/bin/env python3
"""
Tests for markwhen parser
"""

import tempfile
from datetime import datetime
from pathlib import Path

from .main import MarkwhenParser
from .fixtures.expected import (
    EXPECTED_FRONTMATTER_BASIC,
    EXPECTED_FRONTMATTER_TIMELINE,
    EXPECTED_FRONTMATTER_TEST,
    get_expected_event_basic,
    get_expected_event_with_tags,
    get_expected_event_with_links,
    get_expected_event_with_properties,
    get_expected_full_timeline_parse,
    get_expected_last_event_parse,
    assert_event_matches
)


def get_fixture_path(filename: str) -> Path:
    """Get path to a fixture file"""
    return Path(__file__).parent / "fixtures" / filename


def test_parse_frontmatter():
    """Test frontmatter parsing"""
    parser = MarkwhenParser()
    
    # Load fixture file
    fixture_path = get_fixture_path("frontmatter_basic.markwhen")
    with open(fixture_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    frontmatter, end_idx = parser.parse_frontmatter(lines)
    
    # Compare with expected output
    assert frontmatter == EXPECTED_FRONTMATTER_BASIC
    assert end_idx == 4
    print("✓ test_parse_frontmatter passed")


def test_parse_event():
    """Test event parsing"""
    parser = MarkwhenParser()
    
    # Test ISO8601 format
    event = parser.parse_event_line("2025-01-15T10:30:00: App Name")
    assert event is not None
    assert_event_matches(event, get_expected_event_basic())
    
    # Test with tags - load from fixture
    fixture_path = get_fixture_path("event_with_tags.markwhen")
    with open(fixture_path, 'r', encoding='utf-8') as f:
        event_line = f.read().strip()
    event = parser.parse_event_line(event_line)
    assert event is not None
    assert_event_matches(event, get_expected_event_with_tags())
    
    # Test with links - load from fixture
    fixture_path = get_fixture_path("event_with_links.markwhen")
    with open(fixture_path, 'r', encoding='utf-8') as f:
        event_line = f.read().strip()
    event = parser.parse_event_line(event_line)
    assert event is not None
    assert_event_matches(event, get_expected_event_with_links())
    
    # Test comment
    event = parser.parse_event_line("// This is a comment")
    assert event is None
    
    print("✓ test_parse_event passed")


def test_parse_event_with_properties():
    """Test parsing event with properties"""
    parser = MarkwhenParser()
    
    # Load fixture file
    fixture_path = get_fixture_path("event_with_properties.markwhen")
    result = parser.parse_file(fixture_path)
    
    assert len(result['events']) == 1
    assert_event_matches(result['events'][0], get_expected_event_with_properties())
    
    print("✓ test_parse_event_with_properties passed")


def test_parse_file():
    """Test full file parsing"""
    parser = MarkwhenParser()
    
    # Load fixture file
    fixture_path = get_fixture_path("full_timeline.markwhen")
    result = parser.parse_file(fixture_path)
    
    # Compare with expected output
    expected = get_expected_full_timeline_parse()
    assert result['frontmatter'] == expected['frontmatter']
    assert len(result['events']) == len(expected['events'])
    
    for actual_event, expected_event_dict in zip(result['events'], expected['events']):
        assert_event_matches(actual_event, expected_event_dict)
    
    print("✓ test_parse_file passed")


def test_parse_last_event():
    """Test parsing last event"""
    parser = MarkwhenParser()
    
    # Load fixture file
    fixture_path = get_fixture_path("last_event_test.markwhen")
    last_app = parser.parse_last_event(fixture_path)
    
    # Verify against expected output
    expected = get_expected_last_event_parse()
    assert last_app == expected['events'][-1]['description']
    
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
    
    # Use temporary file for this test
    with tempfile.NamedTemporaryFile(mode='w', suffix='.markwhen', delete=False) as f:
        test_file = Path(f.name)
    
    try:
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
    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()
    
    print("✓ test_append_event passed")


def run_all_tests():
    """Run all tests"""
    print("Running markwhen parser tests...")
    print()
    
    try:
        test_parse_frontmatter()
        test_parse_event()
        test_parse_event_with_properties()
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

