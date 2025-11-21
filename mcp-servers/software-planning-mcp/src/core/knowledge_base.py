import os
import json
import sqlite3
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from loguru import logger

class KnowledgeBaseManager:
    """
    Manages the knowledge base for the Software Planning MCP.
    Provides centralized storage for project documentation, technical documentation,
    decision history, and best practices.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        # Default knowledge base location
        if db_path is None:
            db_path = os.path.expanduser("~/.mcp/knowledge_base.db")
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
    
    async def initialize(self) -> None:
        """
        Initialize the knowledge base.
        Creates necessary tables in the SQLite database.
        """
        logger.info("Initializing knowledge base")
        
        # Initialize database in a thread to avoid blocking
        def init_db():
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            
            # Create documents table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    document_type TEXT NOT NULL,
                    project_id TEXT,
                    tags TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            # Create decisions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS decisions (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    rationale TEXT NOT NULL,
                    alternatives TEXT,
                    project_id TEXT,
                    tags TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            # Create best_practices table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS best_practices (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT NOT NULL,
                    tags TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                )
            ''')
            
            # Create search index
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS search_index
                USING fts5(id, title, content, tags)
            ''')
            
            self.conn.commit()
            return True
        
        try:
            # Run database initialization in a thread
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, init_db)
            
            if result:
                logger.info("Knowledge base initialized successfully")
                
                # Initialize with basic best practices if the table is empty
                count = await self._count_best_practices()
                if count == 0:
                    await self._initialize_default_best_practices()
            else:
                logger.error("Failed to initialize knowledge base")
        except Exception as e:
            logger.error(f"Error initializing knowledge base: {e}")
            raise
    
    async def _count_best_practices(self) -> int:
        """Count the number of best practices in the database."""
        def count():
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM best_practices")
            return cursor.fetchone()[0]
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, count)
    
    async def _initialize_default_best_practices(self) -> None:
        """Initialize the database with default best practices."""
        default_practices = [
            {
                "id": "bp-1",
                "title": "Use semantic versioning",
                "description": "Semantic versioning is a versioning system that uses a three-part version number (MAJOR.MINOR.PATCH) to convey meaning about the changes made.",
                "category": "versioning",
                "tags": "versioning,release,deployment",
            },
            {
                "id": "bp-2",
                "title": "Write comprehensive tests",
                "description": "Tests should cover all business logic and edge cases. Aim for high test coverage to ensure code quality and prevent regressions.",
                "category": "testing",
                "tags": "testing,quality,development",
            },
            {
                "id": "bp-3",
                "title": "Use dependency injection",
                "description": "Dependency injection is a design pattern that allows a service to receive its dependencies from external sources rather than creating them itself.",
                "category": "design_patterns",
                "tags": "design,architecture,patterns",
            },
            {
                "id": "bp-4",
                "title": "Document public APIs",
                "description": "All public APIs should be thoroughly documented with examples, parameter descriptions, and return value specifications.",
                "category": "documentation",
                "tags": "documentation,api,development",
            },
            {
                "id": "bp-5",
                "title": "Follow the Single Responsibility Principle",
                "description": "A class or module should have one, and only one, reason to change. This principle helps maintain clean and modular code.",
                "category": "design_principles",
                "tags": "solid,architecture,design",
            },
        ]
        
        for practice in default_practices:
            await self.add_best_practice(
                title=practice["title"],
                description=practice["description"],
                category=practice["category"],
                tags=practice["tags"].split(","),
                custom_id=practice["id"]
            )
        
        logger.info(f"Initialized knowledge base with {len(default_practices)} default best practices")
    
    async def add_document(
        self,
        title: str,
        content: str,
        document_type: str,
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        custom_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a document to the knowledge base.
        
        Args:
            title: The title of the document
            content: The content of the document
            document_type: The type of document (e.g., "requirements", "architecture", "api_spec")
            project_id: Optional project ID that this document belongs to
            tags: Optional list of tags for the document
            custom_id: Optional custom ID for the document
            metadata: Optional metadata for the document
            
        Returns:
            The ID of the added document
        """
        doc_id = custom_id or f"doc-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(title) % 10000}"
        now = datetime.now().isoformat()
        
        def insert_doc():
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                INSERT INTO documents (id, title, content, document_type, project_id, tags, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    doc_id,
                    title,
                    content,
                    document_type,
                    project_id,
                    json.dumps(tags or []),
                    now,
                    now,
                    json.dumps(metadata or {})
                )
            )
            
            # Update search index
            tag_str = " ".join(tags or [])
            cursor.execute(
                '''
                INSERT INTO search_index (id, title, content, tags)
                VALUES (?, ?, ?, ?)
                ''',
                (doc_id, title, content, tag_str)
            )
            
            self.conn.commit()
            return doc_id
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, insert_doc)
    
    async def add_decision(
        self,
        title: str,
        description: str,
        rationale: str,
        alternatives: Optional[List[Dict[str, str]]] = None,
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        custom_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a decision to the knowledge base.
        
        Args:
            title: The title of the decision
            description: The description of the decision
            rationale: The rationale for the decision
            alternatives: Optional list of alternative options that were considered
            project_id: Optional project ID that this decision belongs to
            tags: Optional list of tags for the decision
            custom_id: Optional custom ID for the decision
            metadata: Optional metadata for the decision
            
        Returns:
            The ID of the added decision
        """
        decision_id = custom_id or f"decision-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(title) % 10000}"
        now = datetime.now().isoformat()
        
        def insert_decision():
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                INSERT INTO decisions (id, title, description, rationale, alternatives, project_id, tags, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    decision_id,
                    title,
                    description,
                    rationale,
                    json.dumps(alternatives or []),
                    project_id,
                    json.dumps(tags or []),
                    now,
                    now,
                    json.dumps(metadata or {})
                )
            )
            
            # Update search index
            content = f"{description} {rationale}"
            if alternatives:
                for alt in alternatives:
                    content += f" {alt.get('description', '')} {alt.get('rationale', '')}"
            
            tag_str = " ".join(tags or [])
            cursor.execute(
                '''
                INSERT INTO search_index (id, title, content, tags)
                VALUES (?, ?, ?, ?)
                ''',
                (decision_id, title, content, tag_str)
            )
            
            self.conn.commit()
            return decision_id
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, insert_decision)
    
    async def add_best_practice(
        self,
        title: str,
        description: str,
        category: str,
        tags: Optional[List[str]] = None,
        custom_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Add a best practice to the knowledge base.
        
        Args:
            title: The title of the best practice
            description: The description of the best practice
            category: The category of the best practice
            tags: Optional list of tags for the best practice
            custom_id: Optional custom ID for the best practice
            metadata: Optional metadata for the best practice
            
        Returns:
            The ID of the added best practice
        """
        practice_id = custom_id or f"bp-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hash(title) % 10000}"
        now = datetime.now().isoformat()
        
        def insert_practice():
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                INSERT INTO best_practices (id, title, description, category, tags, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    practice_id,
                    title,
                    description,
                    category,
                    json.dumps(tags or []),
                    now,
                    now,
                    json.dumps(metadata or {})
                )
            )
            
            # Update search index
            tag_str = " ".join(tags or [])
            cursor.execute(
                '''
                INSERT INTO search_index (id, title, content, tags)
                VALUES (?, ?, ?, ?)
                ''',
                (practice_id, title, description, tag_str)
            )
            
            self.conn.commit()
            return practice_id
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, insert_practice)
    
    async def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search the knowledge base for documents, decisions, and best practices.
        
        Args:
            query: The search query
            limit: The maximum number of results to return
            
        Returns:
            A list of search results
        """
        def execute_search():
            cursor = self.conn.cursor()
            cursor.execute(
                '''
                SELECT id, title, snippet(search_index, 2, '<mark>', '</mark>', '...', 10) as snippet
                FROM search_index
                WHERE search_index MATCH ?
                ORDER BY rank
                LIMIT ?
                ''',
                (query, limit)
            )
            results = []
            for row in cursor.fetchall():
                item_id, title, snippet = row
                
                # Determine item type from ID
                item_type = None
                if item_id.startswith("doc-"):
                    item_type = "document"
                elif item_id.startswith("decision-"):
                    item_type = "decision"
                elif item_id.startswith("bp-"):
                    item_type = "best_practice"
                
                results.append({
                    "id": item_id,
                    "title": title,
                    "snippet": snippet,
                    "type": item_type
                })
            
            return results
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, execute_search)
    
    async def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID."""
        def fetch_doc():
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, title, content, document_type, project_id, tags, created_at, updated_at, metadata FROM documents WHERE id = ?",
                (doc_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            
            id, title, content, doc_type, project_id, tags_json, created_at, updated_at, metadata_json = row
            return {
                "id": id,
                "title": title,
                "content": content,
                "document_type": doc_type,
                "project_id": project_id,
                "tags": json.loads(tags_json),
                "created_at": created_at,
                "updated_at": updated_at,
                "metadata": json.loads(metadata_json)
            }
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, fetch_doc)
    
    async def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Get a decision by ID."""
        def fetch_decision():
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, title, description, rationale, alternatives, project_id, tags, created_at, updated_at, metadata FROM decisions WHERE id = ?",
                (decision_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            
            id, title, description, rationale, alternatives_json, project_id, tags_json, created_at, updated_at, metadata_json = row
            return {
                "id": id,
                "title": title,
                "description": description,
                "rationale": rationale,
                "alternatives": json.loads(alternatives_json),
                "project_id": project_id,
                "tags": json.loads(tags_json),
                "created_at": created_at,
                "updated_at": updated_at,
                "metadata": json.loads(metadata_json)
            }
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, fetch_decision)
    
    async def get_best_practice(self, practice_id: str) -> Optional[Dict[str, Any]]:
        """Get a best practice by ID."""
        def fetch_practice():
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT id, title, description, category, tags, created_at, updated_at, metadata FROM best_practices WHERE id = ?",
                (practice_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            
            id, title, description, category, tags_json, created_at, updated_at, metadata_json = row
            return {
                "id": id,
                "title": title,
                "description": description,
                "category": category,
                "tags": json.loads(tags_json),
                "created_at": created_at,
                "updated_at": updated_at,
                "metadata": json.loads(metadata_json)
            }
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, fetch_practice)
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get tools for knowledge base operations."""
        return [
            {
                "name": "search_knowledge_base",
                "description": "Search the knowledge base for documents, decisions, and best practices",
                "parameters": [
                    {
                        "name": "query",
                        "description": "The search query",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "limit",
                        "description": "The maximum number of results to return",
                        "type": "integer",
                        "required": False,
                        "default": 10,
                    }
                ],
                "handler": self.tool_search_knowledge_base,
            },
            {
                "name": "add_document",
                "description": "Add a document to the knowledge base",
                "parameters": [
                    {
                        "name": "title",
                        "description": "The title of the document",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "content",
                        "description": "The content of the document",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "document_type",
                        "description": "The type of document (e.g., 'requirements', 'architecture', 'api_spec')",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "project_id",
                        "description": "The project ID that this document belongs to",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "tags",
                        "description": "List of tags for the document",
                        "type": "array",
                        "items": {"type": "string"},
                        "required": False,
                    }
                ],
                "handler": self.tool_add_document,
            },
            {
                "name": "add_decision",
                "description": "Add a decision to the knowledge base",
                "parameters": [
                    {
                        "name": "title",
                        "description": "The title of the decision",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "description",
                        "description": "The description of the decision",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "rationale",
                        "description": "The rationale for the decision",
                        "type": "string",
                        "required": True,
                    },
                    {
                        "name": "alternatives",
                        "description": "List of alternative options that were considered",
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "rationale": {"type": "string"}
                            }
                        },
                        "required": False,
                    },
                    {
                        "name": "project_id",
                        "description": "The project ID that this decision belongs to",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "tags",
                        "description": "List of tags for the decision",
                        "type": "array",
                        "items": {"type": "string"},
                        "required": False,
                    }
                ],
                "handler": self.tool_add_decision,
            },
            {
                "name": "get_best_practices",
                "description": "Get best practices from the knowledge base",
                "parameters": [
                    {
                        "name": "category",
                        "description": "Filter by category (optional)",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "tag",
                        "description": "Filter by tag (optional)",
                        "type": "string",
                        "required": False,
                    },
                    {
                        "name": "limit",
                        "description": "The maximum number of results to return",
                        "type": "integer",
                        "required": False,
                        "default": 10,
                    }
                ],
                "handler": self.tool_get_best_practices,
            },
        ]
    
    async def tool_search_knowledge_base(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Tool handler for searching the knowledge base."""
        results = await self.search(query, limit)
        return {"results": results}
    
    async def tool_add_document(
        self, title: str, content: str, document_type: str, project_id: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Tool handler for adding a document to the knowledge base."""
        doc_id = await self.add_document(title, content, document_type, project_id, tags)
        return {"id": doc_id, "message": f"Document '{title}' added to knowledge base"}
    
    async def tool_add_decision(
        self, title: str, description: str, rationale: str, 
        alternatives: Optional[List[Dict[str, str]]] = None,
        project_id: Optional[str] = None, 
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Tool handler for adding a decision to the knowledge base."""
        decision_id = await self.add_decision(title, description, rationale, alternatives, project_id, tags)
        return {"id": decision_id, "message": f"Decision '{title}' added to knowledge base"}
    
    async def tool_get_best_practices(
        self, category: Optional[str] = None, tag: Optional[str] = None, limit: int = 10
    ) -> Dict[str, Any]:
        """Tool handler for getting best practices from the knowledge base."""
        def fetch_practices():
            cursor = self.conn.cursor()
            query = "SELECT id, title, description, category, tags FROM best_practices"
            params = []
            
            # Add filters if provided
            where_clauses = []
            if category:
                where_clauses.append("category = ?")
                params.append(category)
            
            if tag:
                where_clauses.append("tags LIKE ?")
                params.append(f"%{tag}%")  # Simple substring match for now
            
            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)
            
            query += " LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            practices = []
            for row in cursor.fetchall():
                id, title, description, category, tags_json = row
                practices.append({
                    "id": id,
                    "title": title,
                    "description": description,
                    "category": category,
                    "tags": json.loads(tags_json)
                })
            return practices
        
        loop = asyncio.get_event_loop()
        practices = await loop.run_in_executor(None, fetch_practices)
        return {"best_practices": practices}
