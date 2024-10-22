from datetime import date, datetime, timezone

def convert_timestamp_to_iso(timestamp):
    """Convert a Unix timestamp (in milliseconds) to ISO 8601 format."""
    return datetime.fromtimestamp(timestamp / 1000, timezone.utc).isoformat()

import streamlit as st
def clean_alerts(indicators):
    """Remove alert entries with null condition, trigger, and expiration."""
    for indicator in indicators:
        if 'alerts' in indicator:
            indicator['alerts'] = [
                alert for alert in indicator['alerts']
                if not (alert['condition'] is None and
                        alert['trigger'] is None and
                        alert['expiration'] is None)
            ]
            # if not indicator['alerts']:
            #     del indicator['alerts']
    return indicators


def is_valid_string(value):
    return isinstance(value, str) and bool(value.strip())


