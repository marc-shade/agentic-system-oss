#!/usr/bin/env python3
"""
Filesystem Integration Tools for FastMCP

Filesystem integration for attaching documents to agents with semantic search.
Based on Letta's filesystem pattern with Qdrant vector search integration.

Features:
- Folder attachment to agents
- File content indexing with embeddings
- Semantic file search using Qdrant
- Simple filename matching fallback
"""
import platform

import logging
import sqlite3
import hashlib
from typing import Dict, Any, List, Optional
from pathlib import Path
import os

logger = logging.getLogger(__name__)

# Supported file extensions for content indexing
INDEXABLE_EXTENSIONS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.go', '.rs', '.c', '.cpp', '.h',
    '.md', '.txt', '.rst', '.yaml', '.yml', '.json', '.toml', '.ini', '.cfg',
    '.html', '.css', '.scss', '.sh', '.bash', '.zsh', '.fish',
    '.sql', '.graphql', '.proto', '.xml', '.csv'
}

# Maximum file size for indexing (1MB)
MAX_FILE_SIZE_BYTES = 1024 * 1024

# Qdrant configuration
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = os.environ.get("QDRANT_PORT", "6333")
QDRANT_URL = f"http://{QDRANT_HOST}:{QDRANT_PORT}"
FILE_COLLECTION_NAME = "agent_files"

# Database path
MEMORY_DIR = Path.home() / ".claude" / "enhanced_memories"
DB_PATH = MEMORY_DIR / "memory.db"


def register_filesystem_tools(app, db_path, nmf=None):
    """Register filesystem tools with FastMCP app including semantic search

    Args:
        app: FastMCP application instance
        db_path: Path to SQLite database
        nmf: Neural Memory Fabric instance for embeddings (optional)
    """

    def _init_filesystem_tables():
        """Initialize filesystem tables in database"""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL,
                folder_name TEXT NOT NULL,
                folder_path TEXT NOT NULL,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(agent_id, folder_name)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agent_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                folder_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size_bytes INTEGER,
                content_hash TEXT,
                indexed_at TIMESTAMP,
                qdrant_id TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (folder_id) REFERENCES agent_folders (id) ON DELETE CASCADE
            )
        ''')

        # Index for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_agent_files_hash ON agent_files(content_hash)
        ''')

        conn.commit()
        conn.close()

    _init_filesystem_tables()

    @app.tool()
    async def create_agent_folder(
        agent_id: str,
        folder_name: str,
        folder_path: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a folder attachment for an agent (simplified).

        Args:
            agent_id: Agent identifier
            folder_name: Logical name for the folder
            folder_path: Actual filesystem path
            description: Optional folder description

        Returns:
            Folder creation result

        Example:
            create_agent_folder(
                agent_id="my_agent",
                folder_name="architecture_docs",
                folder_path=os.path.join(os.environ.get("AGENTIC_SYSTEM_PATH", str(_STORAGE_BASE)), "docs"),
                description="System architecture documentation"
            )
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO agent_folders (agent_id, folder_name, folder_path, description)
                VALUES (?, ?, ?, ?)
            ''', (agent_id, folder_name, folder_path, description))

            folder_id = cursor.lastrowid
            conn.commit()

            return {
                "success": True,
                "folder_id": folder_id,
                "agent_id": agent_id,
                "folder_name": folder_name,
                "folder_path": folder_path
            }
        except sqlite3.IntegrityError:
            return {
                "success": False,
                "error": f"Folder '{folder_name}' already exists for agent '{agent_id}'"
            }
        finally:
            conn.close()

    @app.tool()
    async def list_agent_folders(agent_id: str) -> Dict[str, Any]:
        """
        List all folders attached to an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            List of attached folders

        Example:
            list_agent_folders(agent_id="my_agent")
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, folder_name, folder_path, description, created_at
            FROM agent_folders
            WHERE agent_id = ?
            ORDER BY created_at
        ''', (agent_id,))

        folders = []
        for row in cursor.fetchall():
            # Count files in folder
            cursor.execute('''
                SELECT COUNT(*) FROM agent_files WHERE folder_id = ?
            ''', (row[0],))
            file_count = cursor.fetchone()[0]

            folders.append({
                "folder_id": row[0],
                "folder_name": row[1],
                "folder_path": row[2],
                "description": row[3],
                "created_at": row[4],
                "file_count": file_count
            })

        conn.close()

        return {
            "success": True,
            "agent_id": agent_id,
            "count": len(folders),
            "folders": folders
        }

    @app.tool()
    async def simple_file_search(
        agent_id: str,
        query: str
    ) -> Dict[str, Any]:
        """
        Simple file search in attached folders (filename matching).

        Note: This is a simplified implementation. Full semantic search
        with Qdrant embeddings will be added in future versions.

        Args:
            agent_id: Agent identifier
            query: Search query (filename pattern)

        Returns:
            Matching files

        Example:
            simple_file_search(agent_id="my_agent", query="CLAUDE.md")
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get folders for this agent
        cursor.execute('''
            SELECT id, folder_path FROM agent_folders WHERE agent_id = ?
        ''', (agent_id,))

        folders = cursor.fetchall()
        matches = []

        for folder_id, folder_path in folders:
            # Search files in folder
            folder = Path(folder_path)
            if folder.exists():
                for file in folder.rglob(f"*{query}*"):
                    if file.is_file():
                        matches.append({
                            "filename": file.name,
                            "path": str(file),
                            "size_kb": file.stat().st_size / 1024
                        })

        conn.close()

        return {
            "success": True,
            "agent_id": agent_id,
            "query": query,
            "count": len(matches),
            "matches": matches[:20]  # Limit to 20 results
        }

    def _ensure_qdrant_collection():
        """Ensure Qdrant collection exists for file embeddings"""
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            client = QdrantClient(url=QDRANT_URL)

            # Check if collection exists
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]

            if FILE_COLLECTION_NAME not in collection_names:
                # Create collection with 768-dim vectors (standard embedding size)
                client.create_collection(
                    collection_name=FILE_COLLECTION_NAME,
                    vectors_config=VectorParams(
                        size=768,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created Qdrant collection: {FILE_COLLECTION_NAME}")

            return True
        except Exception as e:
            logger.error(f"Failed to ensure Qdrant collection: {e}")
            return False

    def _compute_file_hash(file_path: Path) -> str:
        """Compute SHA256 hash of file contents"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    @app.tool()
    async def index_folder_files(
        agent_id: str,
        folder_name: str,
        force_reindex: bool = False
    ) -> Dict[str, Any]:
        """
        Index all files in an agent's folder for semantic search.

        Generates embeddings for file contents and stores them in Qdrant
        for fast semantic similarity search. Only indexes files with
        supported extensions that are under 1MB.

        Args:
            agent_id: Agent identifier
            folder_name: Name of the folder to index
            force_reindex: If True, re-index files even if already indexed

        Returns:
            Indexing result with statistics

        Example:
            index_folder_files(
                agent_id="my_agent",
                folder_name="architecture_docs",
                force_reindex=False
            )
        """
        if nmf is None:
            return {
                "success": False,
                "error": "Neural Memory Fabric not available - cannot generate embeddings"
            }

        # Ensure Qdrant collection exists
        if not _ensure_qdrant_collection():
            return {
                "success": False,
                "error": "Failed to initialize Qdrant collection"
            }

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get folder info
        cursor.execute('''
            SELECT id, folder_path FROM agent_folders
            WHERE agent_id = ? AND folder_name = ?
        ''', (agent_id, folder_name))

        row = cursor.fetchone()
        if not row:
            conn.close()
            return {
                "success": False,
                "error": f"Folder '{folder_name}' not found for agent '{agent_id}'"
            }

        folder_id, folder_path = row
        folder = Path(folder_path)

        if not folder.exists():
            conn.close()
            return {
                "success": False,
                "error": f"Folder path does not exist: {folder_path}"
            }

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import PointStruct
            import uuid

            client = QdrantClient(url=QDRANT_URL)

            stats = {
                "files_found": 0,
                "files_indexed": 0,
                "files_skipped": 0,
                "files_too_large": 0,
                "files_unsupported": 0,
                "files_unchanged": 0,
                "errors": []
            }

            points_to_upsert = []

            for file_path in folder.rglob("*"):
                if not file_path.is_file():
                    continue

                stats["files_found"] += 1

                # Check file extension
                if file_path.suffix.lower() not in INDEXABLE_EXTENSIONS:
                    stats["files_unsupported"] += 1
                    continue

                # Check file size
                file_size = file_path.stat().st_size
                if file_size > MAX_FILE_SIZE_BYTES:
                    stats["files_too_large"] += 1
                    continue

                # Compute content hash
                content_hash = _compute_file_hash(file_path)

                # Check if already indexed (unless force_reindex)
                if not force_reindex:
                    cursor.execute('''
                        SELECT qdrant_id FROM agent_files
                        WHERE folder_id = ? AND file_path = ? AND content_hash = ?
                    ''', (folder_id, str(file_path), content_hash))
                    existing = cursor.fetchone()
                    if existing and existing[0]:
                        stats["files_unchanged"] += 1
                        continue

                # Read file content
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                except Exception as e:
                    stats["errors"].append(f"{file_path.name}: {str(e)}")
                    stats["files_skipped"] += 1
                    continue

                # Truncate content for embedding (keep first 8000 chars)
                content_for_embedding = content[:8000] if len(content) > 8000 else content

                # Generate embedding
                try:
                    embedding_result = await nmf.embedding_manager.generate_embedding(content_for_embedding)
                    embedding = (
                        embedding_result.embedding
                        if hasattr(embedding_result, 'embedding')
                        else embedding_result.get("embedding", embedding_result.get("vector", []))
                    )
                except Exception as e:
                    stats["errors"].append(f"{file_path.name}: Embedding failed - {str(e)}")
                    stats["files_skipped"] += 1
                    continue

                # Create Qdrant point
                point_id = str(uuid.uuid4())
                points_to_upsert.append(PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "agent_id": agent_id,
                        "folder_id": folder_id,
                        "folder_name": folder_name,
                        "filename": file_path.name,
                        "file_path": str(file_path),
                        "file_size_bytes": file_size,
                        "content_hash": content_hash,
                        "extension": file_path.suffix.lower(),
                        "content_preview": content[:500]  # First 500 chars as preview
                    }
                ))

                # Update database record
                cursor.execute('''
                    INSERT OR REPLACE INTO agent_files
                    (folder_id, filename, file_path, file_size_bytes, content_hash, indexed_at, qdrant_id)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                ''', (folder_id, file_path.name, str(file_path), file_size, content_hash, point_id))

                stats["files_indexed"] += 1

            # Batch upsert to Qdrant
            if points_to_upsert:
                client.upsert(
                    collection_name=FILE_COLLECTION_NAME,
                    points=points_to_upsert
                )

            conn.commit()
            conn.close()

            return {
                "success": True,
                "agent_id": agent_id,
                "folder_name": folder_name,
                "folder_path": folder_path,
                "statistics": stats
            }

        except Exception as e:
            conn.close()
            logger.error(f"Error indexing folder: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def semantic_file_search(
        agent_id: str,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Search files using semantic similarity.

        Finds files whose content is semantically similar to the query,
        even if they don't contain the exact keywords.

        Args:
            agent_id: Agent identifier
            query: Natural language search query
            limit: Maximum number of results (default: 10)
            score_threshold: Minimum similarity score 0.0-1.0 (default: 0.5)

        Returns:
            Matching files with similarity scores

        Example:
            semantic_file_search(
                agent_id="my_agent",
                query="authentication implementation details",
                limit=5
            )
        """
        if nmf is None:
            return {
                "success": False,
                "error": "Neural Memory Fabric not available - cannot perform semantic search"
            }

        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Filter, FieldCondition, MatchValue

            client = QdrantClient(url=QDRANT_URL)

            # Check if collection exists
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]

            if FILE_COLLECTION_NAME not in collection_names:
                return {
                    "success": True,
                    "agent_id": agent_id,
                    "query": query,
                    "count": 0,
                    "results": [],
                    "message": "No files have been indexed yet. Use index_folder_files first."
                }

            # Generate query embedding
            embedding_result = await nmf.embedding_manager.generate_embedding(query)
            query_vector = (
                embedding_result.embedding
                if hasattr(embedding_result, 'embedding')
                else embedding_result.get("embedding", embedding_result.get("vector", []))
            )

            # Search with agent filter
            search_filter = Filter(
                must=[
                    FieldCondition(
                        key="agent_id",
                        match=MatchValue(value=agent_id)
                    )
                ]
            )

            results = client.search(
                collection_name=FILE_COLLECTION_NAME,
                query_vector=query_vector,
                query_filter=search_filter,
                limit=limit,
                score_threshold=score_threshold
            )

            matches = []
            for hit in results:
                matches.append({
                    "filename": hit.payload.get("filename"),
                    "file_path": hit.payload.get("file_path"),
                    "folder_name": hit.payload.get("folder_name"),
                    "similarity_score": round(hit.score, 4),
                    "file_size_bytes": hit.payload.get("file_size_bytes"),
                    "extension": hit.payload.get("extension"),
                    "content_preview": hit.payload.get("content_preview", "")[:200]
                })

            return {
                "success": True,
                "agent_id": agent_id,
                "query": query,
                "count": len(matches),
                "results": matches
            }

        except Exception as e:
            logger.error(f"Error in semantic file search: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    @app.tool()
    async def get_file_index_status(agent_id: str) -> Dict[str, Any]:
        """
        Get indexing status for all folders attached to an agent.

        Shows which folders are indexed, file counts, and last index time.

        Args:
            agent_id: Agent identifier

        Returns:
            Indexing status for all folders

        Example:
            get_file_index_status(agent_id="my_agent")
        """
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT f.id, f.folder_name, f.folder_path, f.description,
                   COUNT(af.id) as total_files,
                   SUM(CASE WHEN af.qdrant_id IS NOT NULL THEN 1 ELSE 0 END) as indexed_files,
                   MAX(af.indexed_at) as last_indexed
            FROM agent_folders f
            LEFT JOIN agent_files af ON f.id = af.folder_id
            WHERE f.agent_id = ?
            GROUP BY f.id
            ORDER BY f.created_at
        ''', (agent_id,))

        folders = []
        for row in cursor.fetchall():
            folders.append({
                "folder_id": row[0],
                "folder_name": row[1],
                "folder_path": row[2],
                "description": row[3],
                "total_files_tracked": row[4] or 0,
                "indexed_files": row[5] or 0,
                "last_indexed": row[6]
            })

        conn.close()

        # Check Qdrant collection status
        qdrant_status = "unknown"
        total_vectors = 0
        try:
            from qdrant_client import QdrantClient

def _get_storage_base() -> Path:
    """Detect storage base path based on platform."""
    env_path = os.environ.get("AGENTIC_SYSTEM_PATH")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    system = platform.system()
    if system == "Darwin":  # macOS
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    elif system == "Linux":
        if Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
        elif Path(str(_STORAGE_BASE)).exists():
            return Path(str(_STORAGE_BASE))
    return Path(__file__).parent.parent


_STORAGE_BASE = _get_storage_base()

            client = QdrantClient(url=QDRANT_URL)
            collections = client.get_collections().collections
            collection_names = [c.name for c in collections]
            if FILE_COLLECTION_NAME in collection_names:
                info = client.get_collection(FILE_COLLECTION_NAME)
                total_vectors = info.points_count
                qdrant_status = "active"
            else:
                qdrant_status = "collection_not_created"
        except Exception as e:
            qdrant_status = f"error: {str(e)}"

        return {
            "success": True,
            "agent_id": agent_id,
            "folders": folders,
            "qdrant_status": qdrant_status,
            "total_vectors_in_collection": total_vectors
        }

    # Check if semantic search is available
    semantic_available = nmf is not None
    if semantic_available:
        logger.info("✅ Filesystem tools registered (6 tools - with semantic search)")
        logger.info(f"   Qdrant URL: {QDRANT_URL}")
        logger.info(f"   Collection: {FILE_COLLECTION_NAME}")
    else:
        logger.info("✅ Filesystem tools registered (3 tools - simplified)")
        logger.info("   Note: Pass nmf parameter to enable semantic file search")
