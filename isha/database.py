"""
ISHA Database - Simple SQLite Helper

A lightweight database wrapper for SQLite operations.
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class Database:
    """
    Simple SQLite database wrapper.
    
    Usage:
        db = Database("app.db")
        
        # Create table
        db.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                email TEXT
            )
        ''')
        
        # Insert
        db.execute("INSERT INTO users (username, email) VALUES (?, ?)",
                   ("john", "john@example.com"))
        
        # Query
        users = db.query("SELECT * FROM users WHERE username = ?", ("john",))
    """
    
    def __init__(self, database_path: str = ":memory:"):
        """
        Initialize database connection.
        
        Args:
            database_path: Path to SQLite database file (or ":memory:" for in-memory)
        """
        self.database_path = database_path
        self.conn: Optional[sqlite3.Connection] = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish database connection."""
        self.conn = sqlite3.connect(self.database_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Return rows as dictionaries
    
    def execute(self, query: str, params: Tuple = ()) -> sqlite3.Cursor:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters (tuple)
            
        Returns:
            Cursor object
        """
        if not self.conn:
            self._connect()
        
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor
    
    def query(self, query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results.
        
        Args:
            query: SQL SELECT query
            params: Query parameters (tuple)
            
        Returns:
            List of result rows as dictionaries
        """
        cursor = self.execute(query, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def query_one(self, query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
        """
        Execute a SELECT query and return first result.
        
        Args:
            query: SQL SELECT query
            params: Query parameters (tuple)
            
        Returns:
            First result row as dictionary or None
        """
        results = self.query(query, params)
        return results[0] if results else None
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """
        Insert a row into a table.
        
        Args:
            table: Table name
            data: Dictionary of column: value pairs
            
        Returns:
            ID of inserted row
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        cursor = self.execute(query, tuple(data.values()))
        return cursor.lastrowid
    
    def update(self, table: str, data: Dict[str, Any], where: str, params: Tuple = ()) -> int:
        """
        Update rows in a table.
        
        Args:
            table: Table name
            data: Dictionary of column: value pairs to update
            where: WHERE clause (without "WHERE" keyword)
            params: Parameters for WHERE clause
            
        Returns:
            Number of affected rows
        """
        set_clause = ", ".join(f"{col} = ?" for col in data.keys())
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        
        cursor = self.execute(query, tuple(data.values()) + params)
        return cursor.rowcount
    
    def delete(self, table: str, where: str, params: Tuple = ()) -> int:
        """
        Delete rows from a table.
        
        Args:
            table: Table name
            where: WHERE clause (without "WHERE" keyword)
            params: Parameters for WHERE clause
            
        Returns:
            Number of deleted rows
        """
        query = f"DELETE FROM {table} WHERE {where}"
        cursor = self.execute(query, params)
        return cursor.rowcount
    
    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
