"""
Sample Module for AGI System to Practice Improvements

This module contains intentionally suboptimal code that the autonomous
AGI system can detect and improve. It serves as a safe practice target
before the system moves on to improving its own core components.

Each function has optimization opportunities:
- Using loops instead of list comprehensions
- Inefficient algorithms
- Redundant operations
- Suboptimal data structures
"""


def process_items(items):
    """
    Process a list of items by doubling positive values.

    OPTIMIZATION OPPORTUNITY: Uses loop instead of list comprehension.
    Expected improvement: ~20-30% faster with comprehension.

    Args:
        items: List of integers

    Returns:
        List of doubled positive values
    """
    result = []
    for item in items:
        if item > 0:
            result.append(item * 2)
    return result


def calculate_total(numbers):
    """
    Calculate sum of numbers.

    OPTIMIZATION OPPORTUNITY: Manual loop instead of built-in sum().
    Expected improvement: ~15-25% faster with sum().

    Args:
        numbers: List of numbers

    Returns:
        Sum of all numbers
    """
    total = 0
    for num in numbers:
        total += num
    return total


def filter_and_square(values):
    """
    Filter even numbers and return their squares.

    OPTIMIZATION OPPORTUNITY: Nested operations in loop.
    Expected improvement: ~25-35% faster with comprehension.

    Args:
        values: List of integers

    Returns:
        List of squared even numbers
    """
    result = []
    for value in values:
        if value % 2 == 0:
            result.append(value * value)
    return result


def find_max_value(data):
    """
    Find maximum value in list.

    OPTIMIZATION OPPORTUNITY: Manual comparison instead of max().
    Expected improvement: ~30-40% faster with max().

    Args:
        data: List of comparable values

    Returns:
        Maximum value
    """
    if not data:
        return None

    max_val = data[0]
    for val in data:
        if val > max_val:
            max_val = val
    return max_val


def merge_and_sort(list1, list2):
    """
    Merge two lists and sort the result.

    OPTIMIZATION OPPORTUNITY: Separate merge and sort operations.
    Expected improvement: ~20-30% faster with single sorted() call.

    Args:
        list1: First list
        list2: Second list

    Returns:
        Sorted merged list
    """
    result = []
    for item in list1:
        result.append(item)
    for item in list2:
        result.append(item)

    # Bubble sort - intentionally inefficient
    n = len(result)
    for i in range(n):
        for j in range(0, n-i-1):
            if result[j] > result[j+1]:
                result[j], result[j+1] = result[j+1], result[j]

    return result


def count_occurrences(items, target):
    """
    Count how many times target appears in items.

    OPTIMIZATION OPPORTUNITY: Manual loop instead of count().
    Expected improvement: ~25-35% faster with count().

    Args:
        items: List to search
        target: Value to count

    Returns:
        Number of occurrences
    """
    count = 0
    for item in items:
        if item == target:
            count += 1
    return count


def reverse_string(text):
    """
    Reverse a string.

    OPTIMIZATION OPPORTUNITY: Character-by-character loop.
    Expected improvement: ~40-50% faster with slicing [::-1].

    Args:
        text: String to reverse

    Returns:
        Reversed string
    """
    result = ""
    for char in text:
        result = char + result
    return result


def remove_duplicates(items):
    """
    Remove duplicate items from list.

    OPTIMIZATION OPPORTUNITY: Nested loops for duplicate checking.
    Expected improvement: ~60-70% faster with set().

    Args:
        items: List with potential duplicates

    Returns:
        List with duplicates removed
    """
    result = []
    for item in items:
        is_duplicate = False
        for existing in result:
            if item == existing:
                is_duplicate = True
                break
        if not is_duplicate:
            result.append(item)
    return result


def calculate_average(numbers):
    """
    Calculate average of numbers.

    OPTIMIZATION OPPORTUNITY: Separate sum calculation and division.
    Expected improvement: ~20-30% faster with single pass.

    Args:
        numbers: List of numbers

    Returns:
        Average value or None if empty
    """
    if not numbers:
        return None

    total = 0
    for num in numbers:
        total += num

    count = 0
    for _ in numbers:
        count += 1

    return total / count


# Test functions (should not be modified by AGI)
def test_process_items():
    """Test process_items function."""
    assert process_items([1, -2, 3, -4, 5]) == [2, 6, 10]
    assert process_items([]) == []
    assert process_items([-1, -2, -3]) == []
    print("✓ process_items tests passed")


def test_calculate_total():
    """Test calculate_total function."""
    assert calculate_total([1, 2, 3, 4, 5]) == 15
    assert calculate_total([]) == 0
    assert calculate_total([-5, 5]) == 0
    print("✓ calculate_total tests passed")


def test_filter_and_square():
    """Test filter_and_square function."""
    assert filter_and_square([1, 2, 3, 4, 5]) == [4, 16]
    assert filter_and_square([1, 3, 5]) == []
    assert filter_and_square([]) == []
    print("✓ filter_and_square tests passed")


if __name__ == "__main__":
    # Run all tests
    print("Running tests for sample_module...")
    test_process_items()
    test_calculate_total()
    test_filter_and_square()
    print("\n✓ All tests passed!")
