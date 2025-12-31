"""
Deterministic Format Converters

NO AI - Pure code for format conversions.
Following Kai pattern: "If I can do it in code, I do it in code first."
"""

import json
import csv
import io
import base64
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from xml.etree import ElementTree as ET


class FormatConverter:
    """Deterministic format conversions - no AI required."""

    # JSON Conversions
    @staticmethod
    def dict_to_json(data: Dict, indent: int = 2, sort_keys: bool = False) -> str:
        """Convert dict to JSON string."""
        return json.dumps(data, indent=indent, sort_keys=sort_keys, default=str)

    @staticmethod
    def json_to_dict(json_str: str) -> Dict:
        """Convert JSON string to dict."""
        return json.loads(json_str)

    @staticmethod
    def json_to_pretty(json_str: str, indent: int = 2) -> str:
        """Pretty-print JSON string."""
        return json.dumps(json.loads(json_str), indent=indent, default=str)

    # CSV Conversions
    @staticmethod
    def dicts_to_csv(data: List[Dict], fieldnames: Optional[List[str]] = None) -> str:
        """Convert list of dicts to CSV string."""
        if not data:
            return ""
        if fieldnames is None:
            fieldnames = list(data[0].keys())
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()

    @staticmethod
    def csv_to_dicts(csv_str: str) -> List[Dict]:
        """Convert CSV string to list of dicts."""
        reader = csv.DictReader(io.StringIO(csv_str))
        return list(reader)

    @staticmethod
    def list_to_csv(data: List[List], headers: Optional[List[str]] = None) -> str:
        """Convert 2D list to CSV string."""
        output = io.StringIO()
        writer = csv.writer(output)
        if headers:
            writer.writerow(headers)
        writer.writerows(data)
        return output.getvalue()

    @staticmethod
    def csv_to_list(csv_str: str, skip_header: bool = False) -> List[List]:
        """Convert CSV string to 2D list."""
        reader = csv.reader(io.StringIO(csv_str))
        data = list(reader)
        if skip_header and data:
            return data[1:]
        return data

    # Markdown Conversions
    @staticmethod
    def dict_to_markdown_table(data: List[Dict], headers: Optional[List[str]] = None) -> str:
        """Convert list of dicts to Markdown table."""
        if not data:
            return ""
        if headers is None:
            headers = list(data[0].keys())

        lines = []
        # Header row
        lines.append("| " + " | ".join(str(h) for h in headers) + " |")
        # Separator
        lines.append("|" + "|".join("---" for _ in headers) + "|")
        # Data rows
        for row in data:
            values = [str(row.get(h, "")) for h in headers]
            lines.append("| " + " | ".join(values) + " |")

        return "\n".join(lines)

    @staticmethod
    def list_to_markdown_list(items: List[str], ordered: bool = False) -> str:
        """Convert list to Markdown list."""
        lines = []
        for i, item in enumerate(items, 1):
            prefix = f"{i}." if ordered else "-"
            lines.append(f"{prefix} {item}")
        return "\n".join(lines)

    @staticmethod
    def dict_to_markdown_definition(data: Dict) -> str:
        """Convert dict to Markdown definition list."""
        lines = []
        for key, value in data.items():
            lines.append(f"**{key}**")
            lines.append(f": {value}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def code_to_markdown(code: str, language: str = "") -> str:
        """Wrap code in Markdown code block."""
        return f"```{language}\n{code}\n```"

    # YAML-like Conversions (basic, no pyyaml dependency)
    @staticmethod
    def dict_to_yaml_like(data: Dict, indent: int = 0) -> str:
        """Convert dict to YAML-like string (simple implementation)."""
        lines = []
        prefix = "  " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(FormatConverter.dict_to_yaml_like(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  -")
                        for k, v in item.items():
                            lines.append(f"{prefix}    {k}: {v}")
                    else:
                        lines.append(f"{prefix}  - {item}")
            else:
                lines.append(f"{prefix}{key}: {value}")
        return "\n".join(lines)

    # XML Conversions
    @staticmethod
    def dict_to_xml(data: Dict, root_name: str = "root") -> str:
        """Convert dict to XML string."""
        def build_element(parent: ET.Element, data: Any):
            if isinstance(data, dict):
                for key, value in data.items():
                    child = ET.SubElement(parent, key)
                    build_element(child, value)
            elif isinstance(data, list):
                for item in data:
                    item_elem = ET.SubElement(parent, "item")
                    build_element(item_elem, item)
            else:
                parent.text = str(data)

        root = ET.Element(root_name)
        build_element(root, data)
        return ET.tostring(root, encoding='unicode')

    @staticmethod
    def xml_to_dict(xml_str: str) -> Dict:
        """Convert XML string to dict (simple implementation)."""
        def element_to_dict(element: ET.Element) -> Union[Dict, str]:
            if len(element) == 0:
                return element.text or ""
            result = {}
            for child in element:
                child_data = element_to_dict(child)
                if child.tag in result:
                    if not isinstance(result[child.tag], list):
                        result[child.tag] = [result[child.tag]]
                    result[child.tag].append(child_data)
                else:
                    result[child.tag] = child_data
            return result

        root = ET.fromstring(xml_str)
        return {root.tag: element_to_dict(root)}

    # Base64 Conversions
    @staticmethod
    def str_to_base64(text: str) -> str:
        """Encode string to base64."""
        return base64.b64encode(text.encode()).decode()

    @staticmethod
    def base64_to_str(encoded: str) -> str:
        """Decode base64 to string."""
        return base64.b64decode(encoded).decode()

    @staticmethod
    def bytes_to_base64(data: bytes) -> str:
        """Encode bytes to base64."""
        return base64.b64encode(data).decode()

    @staticmethod
    def base64_to_bytes(encoded: str) -> bytes:
        """Decode base64 to bytes."""
        return base64.b64decode(encoded)

    # Date/Time Format Conversions
    @staticmethod
    def timestamp_to_iso(ts: float) -> str:
        """Convert Unix timestamp to ISO format."""
        return datetime.fromtimestamp(ts).isoformat()

    @staticmethod
    def iso_to_timestamp(iso_str: str) -> float:
        """Convert ISO format to Unix timestamp."""
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return dt.timestamp()

    @staticmethod
    def reformat_date(date_str: str, from_fmt: str, to_fmt: str) -> str:
        """Convert date string between formats."""
        dt = datetime.strptime(date_str, from_fmt)
        return dt.strftime(to_fmt)

    @staticmethod
    def date_to_human(dt: datetime) -> str:
        """Convert datetime to human-readable string."""
        return dt.strftime("%B %d, %Y at %I:%M %p")

    # Number Format Conversions
    @staticmethod
    def int_to_hex(n: int) -> str:
        """Convert integer to hex string."""
        return hex(n)

    @staticmethod
    def hex_to_int(hex_str: str) -> int:
        """Convert hex string to integer."""
        return int(hex_str, 16)

    @staticmethod
    def int_to_binary(n: int) -> str:
        """Convert integer to binary string."""
        return bin(n)

    @staticmethod
    def binary_to_int(bin_str: str) -> int:
        """Convert binary string to integer."""
        return int(bin_str, 2)

    @staticmethod
    def number_to_words(n: int) -> str:
        """Convert number to words (0-999)."""
        ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine']
        teens = ['ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen',
                 'sixteen', 'seventeen', 'eighteen', 'nineteen']
        tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety']

        if n == 0:
            return 'zero'
        if n < 0:
            return 'negative ' + FormatConverter.number_to_words(-n)
        if n >= 1000:
            return str(n)  # Fall back for large numbers

        result = []
        if n >= 100:
            result.append(ones[n // 100] + ' hundred')
            n %= 100
        if n >= 20:
            result.append(tens[n // 10])
            n %= 10
        elif n >= 10:
            result.append(teens[n - 10])
            n = 0
        if n > 0:
            result.append(ones[n])

        return ' '.join(result).strip()

    # Key Format Conversions
    @staticmethod
    def flatten_dict(data: Dict, separator: str = '.', parent_key: str = '') -> Dict:
        """Flatten nested dict to single level with dotted keys."""
        items = {}
        for key, value in data.items():
            new_key = f"{parent_key}{separator}{key}" if parent_key else key
            if isinstance(value, dict):
                items.update(FormatConverter.flatten_dict(value, separator, new_key))
            else:
                items[new_key] = value
        return items

    @staticmethod
    def unflatten_dict(data: Dict, separator: str = '.') -> Dict:
        """Unflatten dotted keys to nested dict."""
        result = {}
        for key, value in data.items():
            parts = key.split(separator)
            current = result
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = value
        return result


if __name__ == '__main__':
    # Self-test

    # JSON
    data = {"name": "test", "value": 42}
    json_str = FormatConverter.dict_to_json(data)
    assert FormatConverter.json_to_dict(json_str) == data

    # CSV
    records = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
    csv_str = FormatConverter.dicts_to_csv(records)
    restored = FormatConverter.csv_to_dicts(csv_str)
    assert restored[0]['a'] == '1'  # CSV values are strings

    # Markdown table
    table = FormatConverter.dict_to_markdown_table(records)
    assert "| a | b |" in table
    assert "| 1 | 2 |" in table

    # Base64
    original = "Hello, World!"
    encoded = FormatConverter.str_to_base64(original)
    assert FormatConverter.base64_to_str(encoded) == original

    # Date formats
    ts = 1609459200  # 2021-01-01 00:00:00 UTC
    iso = FormatConverter.timestamp_to_iso(ts)
    assert "202" in iso  # Timezone-agnostic (could be 2020-12-31 in some zones)

    # Number formats
    assert FormatConverter.int_to_hex(255) == "0xff"
    assert FormatConverter.hex_to_int("0xff") == 255
    assert FormatConverter.number_to_words(42) == "forty two"

    # Flatten/unflatten
    nested = {"a": {"b": {"c": 1}}}
    flat = FormatConverter.flatten_dict(nested)
    assert flat["a.b.c"] == 1
    assert FormatConverter.unflatten_dict(flat) == nested

    # XML
    xml_str = FormatConverter.dict_to_xml({"item": "value"}, "root")
    assert "<item>value</item>" in xml_str

    print('All FormatConverter tests passed!')
