Database operations using MCP database tools.

Usage:
- /user:database-tools sqlite query "SELECT * FROM users" - SQLite queries
- /user:database-tools postgres connect - PostgreSQL operations
- /user:database-tools vector search "AI documents" - Vector database search
- /user:database-tools es query "products" - Elasticsearch operations
- /user:database-tools backup database_name - Backup operations
- /user:database-tools schema table_name - Show table structure
- /user:database-tools insights "sales trends" - Generate business insights

Example: /user:database-tools sqlite query "SELECT COUNT(*) FROM orders WHERE date > '2024-01-01'"