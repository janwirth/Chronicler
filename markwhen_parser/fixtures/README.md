# Markwhen Parser Test Fixtures

This directory contains test fixtures for the markwhen parser.

## Structure

- **`.markwhen` files**: Sample markwhen timeline files used as input for tests
- **`expected.py`**: Python data structures containing expected output for each test

## Fixture Files

### `frontmatter_basic.markwhen`
Basic frontmatter example with title and timezone.

### `full_timeline.markwhen`
Complete timeline with multiple events, tags, and content lines.

### `last_event_test.markwhen`
Simple timeline for testing last event extraction.

### `event_with_tags.markwhen`
Single event line with tags.

### `event_with_links.markwhen`
Single event line with markdown links.

### `event_with_properties.markwhen`
Event with properties (contact, assignees, location).

## Expected Output

The `expected.py` file contains:
- `EXPECTED_FRONTMATTER_*`: Expected frontmatter dictionaries
- `get_expected_event_*()`: Functions returning expected event data structures
- `get_expected_*_parse()`: Functions returning expected full parse results
- `assert_event_matches()`: Helper function to compare actual vs expected events

## Usage

Tests load fixtures using `get_fixture_path()` and compare results against expected data structures from `expected.py`. This separation makes tests more maintainable and allows fixtures to be reused across different test scenarios.

