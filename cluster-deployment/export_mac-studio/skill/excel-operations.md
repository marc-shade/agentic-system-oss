# Excel Operations

Comprehensive Excel file analysis, comparison, statistics, and data export using excel-mcp.

## File Analysis

**Comprehensive Structure Analysis:**
- Show all worksheets and their structure
- Identify formulas, charts, and pivot tables
- Provide cell counts and data types
- Detect named ranges and formatting
- Display metadata and properties

**Usage:**
```
Analyze file.xlsx for comprehensive analysis
Analyze data.csv sheet:Sales for specific sheet
Analyze report.xlsx format:json for JSON output
```

## Worksheet Comparison

**Compare Two Worksheets:**
- Cell-by-cell differences
- Added/removed rows and columns
- Changed formulas
- Formatting differences
- Complete summary of all changes

**Usage:**
```
Compare Sheet1 in file1.xlsx with Sheet1 in file2.xlsx
Find differences between Q1 and Q2 sales reports
```

**MCP Tool:** `mcp__excel-mcp__compare_worksheets`

## Statistical Analysis

**Column Statistics:**
- Mean, median, mode
- Standard deviation
- Min/max values
- Quartiles and percentiles
- Outlier detection
- Distribution analysis

**Usage:**
```
Get statistics for column B in Sales sheet of data.xlsx
Analyze revenue distribution in financial_report.xlsx
```

**MCP Tool:** `mcp__excel-mcp__analyze_column_statistics`

## Data Export

**Export to Multiple Formats:**

**CSV Export:**
- Standard CSV format
- Custom delimiters
- Quote options

**JSON Export:**
- `records`: List of row objects (default)
- `columns`: Column-oriented structure
- `index`: Include row indices
- `values`: Just the data array

**Markdown Export:**
- Clean markdown tables
- Formatted headers
- Alignment options

**Usage:**
```
Export Sheet1 to CSV format
Convert sales data to JSON with records orientation
Create markdown table from Excel for documentation
```

**MCP Tools:**
- `mcp__excel-mcp__export_to_csv`
- `mcp__excel-mcp__export_to_json`
- `mcp__excel-mcp__export_to_markdown`

## Example Workflows

**Data Quality Check:**
```
1. Analyze data.xlsx - Review structure and data types
2. Get statistics for numeric columns - Identify outliers
3. Compare with previous version - Track changes
4. Export clean data to JSON - Share with team
```

**Report Generation:**
```
1. Analyze quarterly_report.xlsx - Understand structure
2. Calculate statistics for revenue columns
3. Export summary to markdown - Documentation
4. Compare with last quarter - Trend analysis
```

## Token Cost: ~80 tokens
Replaces 4 Excel commands (67 lines, ~268 tokens) = **188 token savings**
