# File Analyzer MCP Server

Cybersecurity file analysis tool using magic numbers to identify true file types.

## Features

- **Magic Number Detection**: Identify file types by header bytes, not extensions
- **Extension Mismatch Detection**: Find files with suspicious extension/content mismatches
- **Hash Calculation**: MD5, SHA1, SHA256 for file integrity and threat lookup
- **Threat Integration**: Check file hashes against threat intelligence feeds
- **Batch Scanning**: Scan directories for suspicious files
- **Entropy Analysis**: Detect potentially encrypted/packed files

## Tools

| Tool | Description |
|------|-------------|
| `identify_file` | Get true file type from magic bytes |
| `calculate_hashes` | Get MD5, SHA1, SHA256 hashes |
| `check_extension_mismatch` | Detect disguised files |
| `scan_directory` | Batch scan for suspicious files |
| `analyze_entropy` | Detect encrypted/packed content |
| `check_file_reputation` | Check hash against threat feeds |

## Magic Numbers Reference

Common file signatures detected:
- **PE Executable**: `4D 5A` (MZ)
- **ELF Binary**: `7F 45 4C 46`
- **PDF**: `25 50 44 46` (%PDF)
- **ZIP/Office**: `50 4B 03 04` (PK)
- **JPEG**: `FF D8 FF`
- **PNG**: `89 50 4E 47`
- **GIF**: `47 49 46 38`
