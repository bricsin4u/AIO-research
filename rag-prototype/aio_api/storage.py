"""
Envelope Storage - SQLite-based metadata storage for ECR.

Why SQLite:
- No server required (single file)
- Fast lookups (indexed)
- Supports structured queries on entities
- Easy to backup (just copy the file)
- Scales to millions of documents

For high-traffic production, add Redis caching on top.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional
from datetime import datetime
from contextlib import contextmanager


class EnvelopeStorage:
    """
    SQLite-based storage for AIO envelopes.
    
    Tables:
    - envelopes: Full envelope JSON + metadata
    - anchors: Individual anchors for fast lookup
    - entities: Extracted entities for structured queries
    """
    
    def __init__(self, db_path: str = "envelopes.db"):
        """
        Initialize storage.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self._init_db()
    
    def _init_db(self):
        """Create tables if they don't exist."""
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS envelopes (
                    envelope_id TEXT PRIMARY KEY,
                    source_uri TEXT NOT NULL,
                    source_type TEXT,
                    created_at TEXT NOT NULL,
                    token_count INTEGER,
                    noise_score REAL,
                    narrative_hash TEXT,
                    envelope_json TEXT NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS anchors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    envelope_id TEXT NOT NULL,
                    anchor_id TEXT NOT NULL,
                    anchor_type TEXT,
                    title TEXT,
                    line_start INTEGER,
                    line_end INTEGER,
                    content TEXT,
                    FOREIGN KEY (envelope_id) REFERENCES envelopes(envelope_id),
                    UNIQUE(envelope_id, anchor_id)
                );
                
                CREATE TABLE IF NOT EXISTS entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    envelope_id TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    anchor_ref TEXT,
                    properties_json TEXT NOT NULL,
                    source_text TEXT,
                    binding_confidence REAL,
                    FOREIGN KEY (envelope_id) REFERENCES envelopes(envelope_id)
                );
                
                CREATE INDEX IF NOT EXISTS idx_anchors_envelope 
                    ON anchors(envelope_id);
                CREATE INDEX IF NOT EXISTS idx_anchors_anchor_id 
                    ON anchors(anchor_id);
                CREATE INDEX IF NOT EXISTS idx_entities_envelope 
                    ON entities(envelope_id);
                CREATE INDEX IF NOT EXISTS idx_entities_type 
                    ON entities(entity_type);
                CREATE INDEX IF NOT EXISTS idx_entities_anchor 
                    ON entities(anchor_ref);
                CREATE INDEX IF NOT EXISTS idx_envelopes_source 
                    ON envelopes(source_uri);
            """)
    
    @contextmanager
    def _get_conn(self):
        """Get database connection with auto-commit."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def store_envelope(self, envelope) -> str:
        """
        Store an envelope and its components.
        
        Args:
            envelope: AIO Envelope object
            
        Returns:
            envelope_id
        """
        envelope_dict = envelope.to_dict()
        
        with self._get_conn() as conn:
            # Store main envelope
            conn.execute("""
                INSERT OR REPLACE INTO envelopes 
                (envelope_id, source_uri, source_type, created_at, 
                 token_count, noise_score, narrative_hash, envelope_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                envelope.id,
                envelope.source.uri,
                envelope.source.type,
                datetime.utcnow().isoformat(),
                envelope.narrative.token_count,
                envelope.narrative.noise_score,
                envelope.integrity.narrative_hash,
                json.dumps(envelope_dict)
            ))
            
            # Delete old anchors/entities for this envelope (for updates)
            conn.execute("DELETE FROM anchors WHERE envelope_id = ?", 
                        (envelope.id,))
            conn.execute("DELETE FROM entities WHERE envelope_id = ?", 
                        (envelope.id,))
            
            # Store anchors with content
            narrative_lines = envelope.narrative.content.split('\n')
            for anchor_id, anchor in envelope.anchors.items():
                content = '\n'.join(
                    narrative_lines[anchor.line_start:anchor.line_end + 1]
                )
                conn.execute("""
                    INSERT INTO anchors 
                    (envelope_id, anchor_id, anchor_type, title, 
                     line_start, line_end, content)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    envelope.id,
                    anchor_id,
                    anchor.type,
                    anchor.title,
                    anchor.line_start,
                    anchor.line_end,
                    content
                ))
            
            # Store entities
            for entity in envelope.entities:
                conn.execute("""
                    INSERT INTO entities 
                    (envelope_id, entity_type, anchor_ref, properties_json,
                     source_text, binding_confidence)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    envelope.id,
                    entity.type,
                    entity.anchor_ref,
                    json.dumps(entity.properties),
                    entity.properties.get('_source', {}).get('text', ''),
                    entity.binding_confidence
                ))
        
        return envelope.id
    
    def get_envelope(self, envelope_id: str) -> Optional[dict]:
        """Get full envelope by ID."""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT envelope_json FROM envelopes WHERE envelope_id = ?",
                (envelope_id,)
            ).fetchone()
            
            if row:
                return json.loads(row['envelope_json'])
            return None
    
    def get_anchor_content(self, envelope_id: str, anchor_id: str) -> Optional[str]:
        """Get content for a specific anchor."""
        # Strip # prefix if present
        anchor_id = anchor_id.lstrip('#')
        
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT content FROM anchors WHERE envelope_id = ? AND anchor_id = ?",
                (envelope_id, anchor_id)
            ).fetchone()
            
            if row:
                return row['content']
            return None

    def get_entities_by_type(self, entity_type: str, limit: int = 100) -> list[dict]:
        """Query entities by type across all envelopes."""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT envelope_id, entity_type, anchor_ref, properties_json,
                       binding_confidence
                FROM entities 
                WHERE entity_type = ?
                LIMIT ?
            """, (entity_type, limit)).fetchall()
            
            return [
                {
                    "envelope_id": row['envelope_id'],
                    "type": row['entity_type'],
                    "anchor_ref": row['anchor_ref'],
                    "properties": json.loads(row['properties_json']),
                    "binding_confidence": row['binding_confidence']
                }
                for row in rows
            ]
    
    def get_entities_by_anchor(self, envelope_id: str, anchor_id: str) -> list[dict]:
        """Get all entities linked to a specific anchor."""
        anchor_ref = f"#{anchor_id}" if not anchor_id.startswith('#') else anchor_id
        
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT entity_type, properties_json, binding_confidence
                FROM entities 
                WHERE envelope_id = ? AND anchor_ref = ?
            """, (envelope_id, anchor_ref)).fetchall()
            
            return [
                {
                    "type": row['entity_type'],
                    "properties": json.loads(row['properties_json']),
                    "binding_confidence": row['binding_confidence']
                }
                for row in rows
            ]
    
    def search_entities(self, query: str, entity_type: str = None, 
                       limit: int = 50) -> list[dict]:
        """
        Search entities by text in properties.
        
        Args:
            query: Text to search for
            entity_type: Optional filter by type
            limit: Max results
        """
        with self._get_conn() as conn:
            if entity_type:
                rows = conn.execute("""
                    SELECT envelope_id, entity_type, anchor_ref, properties_json
                    FROM entities 
                    WHERE entity_type = ? AND properties_json LIKE ?
                    LIMIT ?
                """, (entity_type, f'%{query}%', limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT envelope_id, entity_type, anchor_ref, properties_json
                    FROM entities 
                    WHERE properties_json LIKE ?
                    LIMIT ?
                """, (f'%{query}%', limit)).fetchall()
            
            return [
                {
                    "envelope_id": row['envelope_id'],
                    "type": row['entity_type'],
                    "anchor_ref": row['anchor_ref'],
                    "properties": json.loads(row['properties_json'])
                }
                for row in rows
            ]
    
    def get_stats(self) -> dict:
        """Get storage statistics."""
        with self._get_conn() as conn:
            envelope_count = conn.execute(
                "SELECT COUNT(*) as c FROM envelopes"
            ).fetchone()['c']
            
            anchor_count = conn.execute(
                "SELECT COUNT(*) as c FROM anchors"
            ).fetchone()['c']
            
            entity_count = conn.execute(
                "SELECT COUNT(*) as c FROM entities"
            ).fetchone()['c']
            
            avg_noise = conn.execute(
                "SELECT AVG(noise_score) as avg FROM envelopes"
            ).fetchone()['avg'] or 0
            
            total_tokens = conn.execute(
                "SELECT SUM(token_count) as total FROM envelopes"
            ).fetchone()['total'] or 0
            
            entity_types = conn.execute("""
                SELECT entity_type, COUNT(*) as count 
                FROM entities 
                GROUP BY entity_type
            """).fetchall()
            
            return {
                "envelopes": envelope_count,
                "anchors": anchor_count,
                "entities": entity_count,
                "avg_noise_score": round(avg_noise, 3),
                "total_tokens": total_tokens,
                "entity_types": {row['entity_type']: row['count'] for row in entity_types}
            }
    
    def delete_envelope(self, envelope_id: str) -> bool:
        """Delete an envelope and all its components."""
        with self._get_conn() as conn:
            conn.execute("DELETE FROM entities WHERE envelope_id = ?", (envelope_id,))
            conn.execute("DELETE FROM anchors WHERE envelope_id = ?", (envelope_id,))
            result = conn.execute("DELETE FROM envelopes WHERE envelope_id = ?", 
                                 (envelope_id,))
            return result.rowcount > 0
