"""
Expected output data structures for markwhen parser tests
"""

from typing import Dict, Any, List


# Expected frontmatter outputs
EXPECTED_FRONTMATTER_BASIC: Dict[str, Any] = {
    'title': 'Project plan',
    'timezone': 'America/New_York'
}

EXPECTED_FRONTMATTER_TIMELINE: Dict[str, Any] = {
    'title': 'Test Timeline',
    'date': '2025-01-15'
}

EXPECTED_FRONTMATTER_TEST: Dict[str, Any] = {
    'title': 'Test'
}


# Expected event data structures
def get_expected_event_basic() -> Dict[str, Any]:
    """Expected output for basic ISO8601 event"""
    return {
        'date_str': '2025-01-15T10:30:00',
        'description': 'App Name',
        'tags': [],
        'links': [],
        'references': [],
        'photos': [],
        'properties': {},
        'content_lines': []
    }


def get_expected_event_with_tags() -> Dict[str, Any]:
    """Expected output for event with tags"""
    return {
        'date_str': '2025-01-15T10:30:00',
        'description': 'Project task #Project1 #John',
        'tags': ['#Project1', '#John'],
        'links': [],
        'references': [],
        'photos': [],
        'properties': {},
        'content_lines': []
    }


def get_expected_event_with_links() -> Dict[str, Any]:
    """Expected output for event with links"""
    return {
        'date_str': '2025-01-15T10:30:00',
        'description': 'Check [this link](https://example.com)',
        'tags': [],
        'links': [{'text': 'this link', 'url': 'https://example.com'}],
        'references': [],
        'photos': [],
        'properties': {},
        'content_lines': []
    }


def get_expected_event_with_properties() -> Dict[str, Any]:
    """Expected output for event with properties"""
    return {
        'date_str': '2025-01-15T10:30:00',
        'description': 'Task with properties',
        'tags': [],
        'links': [],
        'references': [],
        'photos': [],
        'properties': {
            'contact': '[email protected]',
            'assignees': '[Michelle, Johnathan]',
            'location': '123 Main Street, Kansas City, MO'
        },
        'content_lines': []
    }


def get_expected_first_app_event() -> Dict[str, Any]:
    """Expected output for first app event in full timeline"""
    return {
        'date_str': '2025-01-15T10:30:00',
        'description': 'First App',
        'tags': [],
        'links': [],
        'references': [],
        'photos': [],
        'properties': {},
        'content_lines': ['  Some content here']
    }


def get_expected_second_app_event() -> Dict[str, Any]:
    """Expected output for second app event in full timeline"""
    return {
        'date_str': '2025-01-15T11:00:00',
        'description': 'Second App #Work',
        'tags': ['#Work'],
        'links': [],
        'references': [],
        'photos': [],
        'properties': {},
        'content_lines': ['  More content', '  - [x] Task 1', '  - [ ] Task 2']
    }


# Expected parse_file outputs
def get_expected_full_timeline_parse() -> Dict[str, Any]:
    """Expected output for parsing full_timeline.markwhen"""
    return {
        'frontmatter': EXPECTED_FRONTMATTER_TIMELINE,
        'events': [
            get_expected_first_app_event(),
            get_expected_second_app_event()
        ]
    }


def get_expected_last_event_parse() -> Dict[str, Any]:
    """Expected output for parsing last_event_test.markwhen"""
    return {
        'frontmatter': EXPECTED_FRONTMATTER_TEST,
        'events': [
            {
                'date_str': '2025-01-15T10:30:00',
                'description': 'First App',
                'tags': [],
                'links': [],
                'references': [],
                'photos': [],
                'properties': {},
                'content_lines': []
            },
            {
                'date_str': '2025-01-15T11:00:00',
                'description': 'Second App',
                'tags': [],
                'links': [],
                'references': [],
                'photos': [],
                'properties': {},
                'content_lines': []
            }
        ]
    }


# Helper function to compare events
def assert_event_matches(actual_event, expected_event_dict: Dict[str, Any]):
    """Assert that an actual MarkwhenEvent matches expected data"""
    assert actual_event.date_str == expected_event_dict['date_str']
    assert actual_event.description == expected_event_dict['description']
    assert actual_event.tags == expected_event_dict['tags']
    assert actual_event.links == expected_event_dict['links']
    assert actual_event.references == expected_event_dict['references']
    assert actual_event.photos == expected_event_dict['photos']
    assert actual_event.properties == expected_event_dict['properties']
    assert actual_event.content_lines == expected_event_dict['content_lines']

