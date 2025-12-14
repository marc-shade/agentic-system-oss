"""
Utility Functions API

Helper functions for filtering, aggregation, and formatting.
Used by agents to transform data before returning to model.
"""

from typing import List, Dict, Any, Optional
import json
from datetime import datetime


def filter_by_confidence(
    results: List[Dict[str, Any]],
    threshold: float
) -> List[Dict[str, Any]]:
    """
    Filter search results by confidence score.

    Example:
        results = search_nodes("optimization", limit=100)
        high_conf = filter_by_confidence(results, 0.8)
        return high_conf  # Only high-confidence results

    Args:
        results: List of search results
        threshold: Minimum confidence score (0.0 to 1.0)

    Returns:
        Filtered list of results
    """
    return [
        r for r in results
        if r.get('confidence', 0.0) >= threshold
    ]


def filter_by_type(
    results: List[Dict[str, Any]],
    entity_type: str
) -> List[Dict[str, Any]]:
    """
    Filter results by entity type.

    Example:
        results = search_nodes("*", limit=1000)
        projects = filter_by_type(results, "project_outcome")
        return summarize_results(projects)
    """
    return [
        r for r in results
        if r.get('entityType') == entity_type
    ]


def filter_by_date_range(
    results: List[Dict[str, Any]],
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Filter results by date range.

    Args:
        results: List of results
        start_date: ISO format date string (inclusive)
        end_date: ISO format date string (inclusive)
    """
    filtered = results

    if start_date:
        filtered = [
            r for r in filtered
            if r.get('created_at', '') >= start_date
        ]

    if end_date:
        filtered = [
            r for r in filtered
            if r.get('created_at', '') <= end_date
        ]

    return filtered


def summarize_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics from results.

    Example:
        results = search_nodes("optimization", limit=100)
        summary = summarize_results(results)
        return {
            "count": summary['count'],
            "avg_confidence": summary['avg_confidence'],
            "top_result": summary['top_result']
        }

    Returns:
        Dictionary with count, types, avg_confidence, top_result
    """
    if not results:
        return {
            "count": 0,
            "types": {},
            "avg_confidence": 0.0,
            "top_result": None
        }

    # Count by type
    types = {}
    for r in results:
        et = r.get('entityType', 'unknown')
        types[et] = types.get(et, 0) + 1

    # Calculate average confidence
    confidences = [r.get('confidence', 0.0) for r in results]
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

    # Get top result (highest confidence)
    top_result = max(results, key=lambda r: r.get('confidence', 0.0))

    return {
        "count": len(results),
        "types": types,
        "avg_confidence": round(avg_confidence, 3),
        "top_result": {
            "name": top_result.get('name'),
            "type": top_result.get('entityType'),
            "confidence": top_result.get('confidence')
        }
    }


def aggregate_stats(
    results: List[Dict[str, Any]],
    field: str
) -> Dict[str, int]:
    """
    Count occurrences of field values.

    Example:
        results = search_nodes("*", limit=1000)
        type_counts = aggregate_stats(results, "entityType")
        return type_counts

    Args:
        results: List of results
        field: Field name to aggregate on

    Returns:
        Dictionary mapping values to counts
    """
    counts = {}
    for r in results:
        value = r.get(field, 'unknown')
        counts[value] = counts.get(value, 0) + 1
    return counts


def aggregate_by_tier(results: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Count results by memory tier.

    Returns distribution across: core, working, reference, archive
    """
    return aggregate_stats(results, 'tier')


def aggregate_by_date(
    results: List[Dict[str, Any]],
    granularity: str = 'day'
) -> Dict[str, int]:
    """
    Aggregate results by date.

    Args:
        granularity: 'day', 'week', or 'month'

    Returns:
        Dictionary mapping date strings to counts
    """
    from collections import defaultdict
    counts = defaultdict(int)

    for r in results:
        created = r.get('created_at')
        if not created:
            continue

        # Parse ISO date string
        if granularity == 'day':
            key = created[:10]  # YYYY-MM-DD
        elif granularity == 'week':
            # Convert to week number
            dt = datetime.fromisoformat(created)
            key = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
        elif granularity == 'month':
            key = created[:7]  # YYYY-MM
        else:
            key = created[:10]

        counts[key] += 1

    return dict(counts)


def format_output(data: Any, format: str = 'summary') -> str:
    """
    Format data for display.

    Example:
        results = search_nodes("optimization", limit=10)
        summary = format_output(results, 'summary')
        return summary

    Args:
        data: Data to format (dict, list, etc.)
        format: 'summary', 'detailed', or 'json'

    Returns:
        Formatted string
    """
    if format == 'json':
        return json.dumps(data, indent=2)

    elif format == 'summary':
        if isinstance(data, list):
            summary = summarize_results(data)
            return f"""
Results Summary:
- Total: {summary['count']}
- Types: {summary['types']}
- Avg Confidence: {summary['avg_confidence']}
- Top: {summary['top_result']['name']} ({summary['top_result']['type']})
            """.strip()
        elif isinstance(data, dict):
            return "\n".join(f"- {k}: {v}" for k, v in data.items())
        else:
            return str(data)

    elif format == 'detailed':
        if isinstance(data, list):
            lines = []
            for i, item in enumerate(data, 1):
                lines.append(f"\n{i}. {item.get('name', 'Unknown')}")
                lines.append(f"   Type: {item.get('entityType', 'unknown')}")
                lines.append(f"   Confidence: {item.get('confidence', 0.0):.3f}")
                if 'observations' in item:
                    lines.append(f"   Observations: {len(item['observations'])}")
            return "\n".join(lines)
        else:
            return json.dumps(data, indent=2)

    return str(data)


def top_n(
    results: List[Dict[str, Any]],
    n: int = 10,
    sort_by: str = 'confidence'
) -> List[Dict[str, Any]]:
    """
    Get top N results sorted by field.

    Example:
        results = search_nodes("*", limit=1000)
        top_10 = top_n(results, 10, 'confidence')
        return format_output(top_10, 'detailed')

    Args:
        results: List of results
        n: Number of results to return
        sort_by: Field to sort by

    Returns:
        Top N results
    """
    sorted_results = sorted(
        results,
        key=lambda r: r.get(sort_by, 0),
        reverse=True
    )
    return sorted_results[:n]


def deduplicate(
    results: List[Dict[str, Any]],
    key: str = 'name'
) -> List[Dict[str, Any]]:
    """
    Remove duplicate results based on key field.

    Keeps first occurrence of each unique value.
    """
    seen = set()
    unique = []

    for r in results:
        value = r.get(key)
        if value not in seen:
            seen.add(value)
            unique.append(r)

    return unique


def combine_results(*result_lists: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Combine multiple result lists and deduplicate.

    Example:
        results1 = search_nodes("optimization", limit=50)
        results2 = search_nodes("performance", limit=50)
        combined = combine_results(results1, results2)
        return summarize_results(combined)
    """
    combined = []
    for result_list in result_lists:
        combined.extend(result_list)

    return deduplicate(combined, 'name')


def calculate_statistics(
    results: List[Dict[str, Any]],
    field: str
) -> Dict[str, float]:
    """
    Calculate statistical measures for a numeric field.

    Returns min, max, mean, median, std_dev
    """
    import statistics

    values = [r.get(field, 0.0) for r in results if field in r]

    if not values:
        return {
            "min": 0.0,
            "max": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "std_dev": 0.0
        }

    return {
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "std_dev": statistics.stdev(values) if len(values) > 1 else 0.0
    }


def extract_field(
    results: List[Dict[str, Any]],
    field: str
) -> List[Any]:
    """
    Extract a single field from all results.

    Example:
        results = search_nodes("project", limit=100)
        names = extract_field(results, "name")
        return names
    """
    return [r.get(field) for r in results if field in r]


def group_by(
    results: List[Dict[str, Any]],
    field: str
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Group results by field value.

    Example:
        results = search_nodes("*", limit=1000)
        by_type = group_by(results, "entityType")
        return {k: len(v) for k, v in by_type.items()}
    """
    from collections import defaultdict
    groups = defaultdict(list)

    for r in results:
        key = r.get(field, 'unknown')
        groups[key].append(r)

    return dict(groups)
