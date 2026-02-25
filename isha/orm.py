"""
Isha ORM — A lightweight Object-Relational Mapper.

Supports SQLite out of the box, with an adapter pattern for PostgreSQL/MySQL.
"""

import sqlite3
import json
import os
import logging
from typing import Any, Dict, List, Optional, Type, Tuple
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("isha.orm")


# ── Field Types ──────────────────────────────────────────────────────

class Field:
    """Base field class for model definitions."""

    def __init__(
        self,
        field_type="TEXT",
        primary_key=False,
        nullable=True,
        default=None,
        unique=False,
        index=False,
    ):
        self.field_type = field_type
        self.primary_key = primary_key
        self.nullable = nullable
        self.default = default
        self.unique = unique
        self.index = index
        self.name = None  # Set by metaclass

    def to_sql(self):
        """Generate SQL column definition."""
        parts = [self.name, self.field_type]
        if self.primary_key:
            parts.append("PRIMARY KEY")
            if self.field_type == "INTEGER":
                parts.append("AUTOINCREMENT")
        if not self.nullable and not self.primary_key:
            parts.append("NOT NULL")
        if self.unique and not self.primary_key:
            parts.append("UNIQUE")
        if self.default is not None:
            if isinstance(self.default, str):
                parts.append(f"DEFAULT '{self.default}'")
            elif isinstance(self.default, bool):
                parts.append(f"DEFAULT {1 if self.default else 0}")
            else:
                parts.append(f"DEFAULT {self.default}")
        return " ".join(parts)

    def python_to_db(self, value):
        """Convert Python value to database value."""
        return value

    def db_to_python(self, value):
        """Convert database value to Python value."""
        return value


class IntegerField(Field):
    def __init__(self, **kwargs):
        super().__init__(field_type="INTEGER", **kwargs)


class TextField(Field):
    def __init__(self, max_length=None, **kwargs):
        self.max_length = max_length
        ft = f"VARCHAR({max_length})" if max_length else "TEXT"
        super().__init__(field_type=ft, **kwargs)


class FloatField(Field):
    def __init__(self, **kwargs):
        super().__init__(field_type="REAL", **kwargs)


class BooleanField(Field):
    def __init__(self, **kwargs):
        super().__init__(field_type="INTEGER", **kwargs)

    def python_to_db(self, value):
        if value is None:
            return None
        return 1 if value else 0

    def db_to_python(self, value):
        if value is None:
            return None
        return bool(value)


class DateTimeField(Field):
    def __init__(self, auto_now=False, auto_now_add=False, **kwargs):
        self.auto_now = auto_now
        self.auto_now_add = auto_now_add
        super().__init__(field_type="TEXT", **kwargs)

    def python_to_db(self, value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)

    def db_to_python(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return value
        return value


class JSONField(Field):
    def __init__(self, **kwargs):
        super().__init__(field_type="TEXT", **kwargs)

    def python_to_db(self, value):
        if value is None:
            return None
        return json.dumps(value)

    def db_to_python(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return json.loads(value)
        return value


class ForeignKeyField(Field):
    def __init__(self, references, on_delete="CASCADE", **kwargs):
        self.references = references  # Model class or "ModelName"
        self.on_delete = on_delete
        super().__init__(field_type="INTEGER", **kwargs)

    def to_sql(self):
        base = super().to_sql()
        ref_table = self.references if isinstance(self.references, str) else self.references.__tablename__
        return f"{base} REFERENCES {ref_table}(id) ON DELETE {self.on_delete}"


# ── Database Adapters ────────────────────────────────────────────────

class DatabaseAdapter:
    """Base database adapter interface."""

    def connect(self):
        raise NotImplementedError

    def execute(self, sql, params=None):
        raise NotImplementedError

    def fetchone(self, sql, params=None):
        raise NotImplementedError

    def fetchall(self, sql, params=None):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError

    def commit(self):
        raise NotImplementedError


class SQLiteAdapter(DatabaseAdapter):
    """SQLite database adapter."""

    def __init__(self, database="isha.db"):
        self.database = database
        self._connection = None

    @property
    def connection(self):
        if self._connection is None:
            self._connection = sqlite3.connect(self.database)
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA journal_mode=WAL")
            self._connection.execute("PRAGMA foreign_keys=ON")
        return self._connection

    def execute(self, sql, params=None):
        logger.debug(f"SQL: {sql} | Params: {params}")
        cursor = self.connection.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        self.connection.commit()
        return cursor

    def fetchone(self, sql, params=None):
        cursor = self.connection.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor.fetchone()

    def fetchall(self, sql, params=None):
        cursor = self.connection.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor.fetchall()

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None

    def commit(self):
        if self._connection:
            self._connection.commit()


# ── Global Database Registry ─────────────────────────────────────────

class Database:
    """Global database connection manager."""

    _adapter: Optional[DatabaseAdapter] = None

    @classmethod
    def configure(cls, adapter: DatabaseAdapter):
        cls._adapter = adapter

    @classmethod
    def connect(cls, database="isha.db", adapter_class=SQLiteAdapter):
        cls._adapter = adapter_class(database)

    @classmethod
    def get_adapter(cls) -> DatabaseAdapter:
        if cls._adapter is None:
            cls.connect()
        return cls._adapter

    @classmethod
    def close(cls):
        if cls._adapter:
            cls._adapter.close()
            cls._adapter = None

    @classmethod
    def execute(cls, sql, params=None):
        return cls.get_adapter().execute(sql, params)

    @classmethod
    def fetchone(cls, sql, params=None):
        return cls.get_adapter().fetchone(sql, params)

    @classmethod
    def fetchall(cls, sql, params=None):
        return cls.get_adapter().fetchall(sql, params)


# ── Query Builder ────────────────────────────────────────────────────

class QueryBuilder:
    """Chainable query builder for the ORM."""

    def __init__(self, model_class):
        self.model_class = model_class
        self._where = []
        self._params = []
        self._order_by = []
        self._limit = None
        self._offset = None
        self._select = "*"

    def filter(self, **kwargs):
        """Add WHERE conditions (AND)."""
        for key, value in kwargs.items():
            # Support operators: field__gt, field__lt, field__gte, field__lte, field__ne, field__like, field__in
            if "__" in key:
                field, op = key.rsplit("__", 1)
                ops = {
                    "gt": ">", "lt": "<", "gte": ">=", "lte": "<=",
                    "ne": "!=", "like": "LIKE", "ilike": "LIKE",
                    "in": "IN", "notin": "NOT IN", "is": "IS",
                }
                if op in ops:
                    if op in ("in", "notin"):
                        placeholders = ", ".join("?" for _ in value)
                        self._where.append(f"{field} {ops[op]} ({placeholders})")
                        self._params.extend(value)
                    else:
                        self._where.append(f"{field} {ops[op]} ?")
                        # Convert Python value for DB
                        field_obj = self.model_class._fields.get(field)
                        if field_obj:
                            value = field_obj.python_to_db(value)
                        self._params.append(value)
                else:
                    self._where.append(f"{key} = ?")
                    self._params.append(value)
            else:
                field_obj = self.model_class._fields.get(key)
                if field_obj:
                    value = field_obj.python_to_db(value)
                self._where.append(f"{key} = ?")
                self._params.append(value)
        return self

    def where(self, condition, *params):
        """Add a raw WHERE condition."""
        self._where.append(condition)
        self._params.extend(params)
        return self

    def order_by(self, *fields):
        """Add ORDER BY clause."""
        for field in fields:
            if field.startswith("-"):
                self._order_by.append(f"{field[1:]} DESC")
            else:
                self._order_by.append(f"{field} ASC")
        return self

    def limit(self, n):
        """Set LIMIT."""
        self._limit = n
        return self

    def offset(self, n):
        """Set OFFSET."""
        self._offset = n
        return self

    def _build_select(self):
        """Build the SELECT SQL query."""
        sql = f"SELECT {self._select} FROM {self.model_class.__tablename__}"
        if self._where:
            sql += " WHERE " + " AND ".join(self._where)
        if self._order_by:
            sql += " ORDER BY " + ", ".join(self._order_by)
        if self._limit is not None:
            sql += f" LIMIT {self._limit}"
        if self._offset is not None:
            sql += f" OFFSET {self._offset}"
        return sql, self._params

    def all(self) -> List:
        """Execute and return all matching records."""
        sql, params = self._build_select()
        rows = Database.fetchall(sql, params)
        return [self.model_class._from_row(dict(row)) for row in rows]

    def first(self):
        """Execute and return the first matching record."""
        self._limit = 1
        sql, params = self._build_select()
        row = Database.fetchone(sql, params)
        if row:
            return self.model_class._from_row(dict(row))
        return None

    def count(self) -> int:
        """Count matching records."""
        self._select = "COUNT(*)"
        sql, params = self._build_select()
        row = Database.fetchone(sql, params)
        return row[0] if row else 0

    def exists(self) -> bool:
        """Check if any matching records exist."""
        return self.count() > 0

    def delete(self) -> int:
        """Delete matching records. Returns count of deleted rows."""
        sql = f"DELETE FROM {self.model_class.__tablename__}"
        if self._where:
            sql += " WHERE " + " AND ".join(self._where)
        cursor = Database.execute(sql, self._params)
        return cursor.rowcount

    def update(self, **kwargs) -> int:
        """Update matching records."""
        sets = []
        set_params = []
        for key, value in kwargs.items():
            field_obj = self.model_class._fields.get(key)
            if field_obj:
                value = field_obj.python_to_db(value)
            sets.append(f"{key} = ?")
            set_params.append(value)

        sql = f"UPDATE {self.model_class.__tablename__} SET " + ", ".join(sets)
        if self._where:
            sql += " WHERE " + " AND ".join(self._where)

        cursor = Database.execute(sql, set_params + self._params)
        return cursor.rowcount


# ── Model Metaclass ──────────────────────────────────────────────────

class ModelMeta(type):
    """Metaclass for Model that collects Field definitions."""

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)

        if name == "Model":
            return cls

        # Collect fields
        fields = {}
        for key, value in namespace.items():
            if isinstance(value, Field):
                value.name = key
                fields[key] = value

        # Inherit fields from parent
        for base in bases:
            if hasattr(base, "_fields"):
                for k, v in base._fields.items():
                    if k not in fields:
                        fields[k] = v

        cls._fields = fields

        # Set table name
        if not hasattr(cls, "__tablename__") or cls.__tablename__ is None:
            cls.__tablename__ = name.lower() + "s"

        return cls


# ── Base Model ───────────────────────────────────────────────────────

class Model(metaclass=ModelMeta):
    """
    Base model class for the Isha ORM.
    
    Example:
        class User(Model):
            __tablename__ = "users"
            
            id = IntegerField(primary_key=True)
            name = TextField(nullable=False)
            email = TextField(unique=True)
            active = BooleanField(default=True)
            created_at = DateTimeField(auto_now_add=True)
        
        # Create table
        User.create_table()
        
        # Create record
        user = User.create(name="Alice", email="alice@example.com")
        
        # Query
        user = User.query().filter(name="Alice").first()
        users = User.query().filter(active=True).order_by("name").all()
    """

    __tablename__ = None
    _fields: Dict[str, Field] = {}

    def __init__(self, **kwargs):
        for field_name, field in self._fields.items():
            value = kwargs.get(field_name, field.default)
            setattr(self, field_name, value)

        # Set auto datetime fields
        for field_name, field in self._fields.items():
            if isinstance(field, DateTimeField):
                if field.auto_now_add and field_name not in kwargs:
                    setattr(self, field_name, datetime.now(timezone.utc))

    @classmethod
    def create_table(cls):
        """Create the database table for this model."""
        columns = []
        for field in cls._fields.values():
            columns.append(field.to_sql())

        sql = f"CREATE TABLE IF NOT EXISTS {cls.__tablename__} ({', '.join(columns)})"
        Database.execute(sql)
        logger.info(f"Created table: {cls.__tablename__}")

        # Create indexes
        for field_name, field in cls._fields.items():
            if field.index:
                idx_name = f"idx_{cls.__tablename__}_{field_name}"
                Database.execute(
                    f"CREATE INDEX IF NOT EXISTS {idx_name} ON {cls.__tablename__}({field_name})"
                )

    @classmethod
    def drop_table(cls):
        """Drop the database table."""
        Database.execute(f"DROP TABLE IF EXISTS {cls.__tablename__}")
        logger.info(f"Dropped table: {cls.__tablename__}")

    @classmethod
    def create(cls, **kwargs):
        """Create and save a new record."""
        instance = cls(**kwargs)
        instance.save()
        return instance

    def save(self):
        """Insert or update this record in the database."""
        fields = {}
        for field_name, field in self._fields.items():
            if field.primary_key and getattr(self, field_name, None) is None:
                continue  # Skip auto-increment PKs on insert

            # Handle auto_now
            if isinstance(field, DateTimeField) and field.auto_now:
                setattr(self, field_name, datetime.now(timezone.utc))

            value = getattr(self, field_name, field.default)
            fields[field_name] = field.python_to_db(value)

        # Determine if INSERT or UPDATE
        pk_field = None
        pk_value = None
        for name, field in self._fields.items():
            if field.primary_key:
                pk_field = name
                pk_value = getattr(self, name, None)
                break

        if pk_value is not None and pk_field:
            # Check if record exists
            existing = Database.fetchone(
                f"SELECT {pk_field} FROM {self.__tablename__} WHERE {pk_field} = ?",
                [pk_value],
            )
            if existing:
                # UPDATE
                sets = []
                params = []
                for k, v in fields.items():
                    if k != pk_field:
                        sets.append(f"{k} = ?")
                        params.append(v)
                params.append(pk_value)
                sql = f"UPDATE {self.__tablename__} SET {', '.join(sets)} WHERE {pk_field} = ?"
                Database.execute(sql, params)
                return self

        # INSERT
        columns = list(fields.keys())
        placeholders = ", ".join("?" for _ in columns)
        values = [fields[c] for c in columns]

        sql = f"INSERT INTO {self.__tablename__} ({', '.join(columns)}) VALUES ({placeholders})"
        cursor = Database.execute(sql, values)

        if pk_field and getattr(self, pk_field, None) is None:
            setattr(self, pk_field, cursor.lastrowid)

        return self

    def delete_record(self):
        """Delete this record from the database."""
        pk_field = None
        pk_value = None
        for name, field in self._fields.items():
            if field.primary_key:
                pk_field = name
                pk_value = getattr(self, name, None)
                break

        if pk_field and pk_value is not None:
            Database.execute(
                f"DELETE FROM {self.__tablename__} WHERE {pk_field} = ?",
                [pk_value],
            )

    @classmethod
    def query(cls) -> QueryBuilder:
        """Start a new query for this model."""
        return QueryBuilder(cls)

    @classmethod
    def get(cls, pk):
        """Get a record by primary key."""
        pk_field = None
        for name, field in cls._fields.items():
            if field.primary_key:
                pk_field = name
                break

        if pk_field is None:
            raise ValueError("Model has no primary key field")

        row = Database.fetchone(
            f"SELECT * FROM {cls.__tablename__} WHERE {pk_field} = ?",
            [pk],
        )
        if row:
            return cls._from_row(dict(row))
        return None

    @classmethod
    def all(cls) -> List:
        """Get all records."""
        rows = Database.fetchall(f"SELECT * FROM {cls.__tablename__}")
        return [cls._from_row(dict(row)) for row in rows]

    @classmethod
    def _from_row(cls, row_dict):
        """Create a model instance from a database row dict."""
        instance = cls.__new__(cls)
        for field_name, field in cls._fields.items():
            raw_value = row_dict.get(field_name)
            setattr(instance, field_name, field.db_to_python(raw_value))
        return instance

    def to_dict(self):
        """Convert model instance to dictionary."""
        result = {}
        for field_name, field in self._fields.items():
            value = getattr(self, field_name, None)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[field_name] = value
        return result

    def __repr__(self):
        pk_field = None
        for name, field in self._fields.items():
            if field.primary_key:
                pk_field = name
                break
        pk_val = getattr(self, pk_field, "?") if pk_field else "?"
        return f"<{self.__class__.__name__} {pk_val}>"


# ── Migration System ────────────────────────────────────────────────

class MigrationManager:
    """Simple migration manager for tracking schema changes."""

    MIGRATION_TABLE = "_isha_migrations"

    @classmethod
    def init(cls):
        """Initialize migration tracking table."""
        Database.execute(f"""
            CREATE TABLE IF NOT EXISTS {cls.MIGRATION_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                applied_at TEXT NOT NULL
            )
        """)

    @classmethod
    def is_applied(cls, name: str) -> bool:
        """Check if a migration has been applied."""
        row = Database.fetchone(
            f"SELECT id FROM {cls.MIGRATION_TABLE} WHERE name = ?",
            [name],
        )
        return row is not None

    @classmethod
    def mark_applied(cls, name: str):
        """Mark a migration as applied."""
        Database.execute(
            f"INSERT INTO {cls.MIGRATION_TABLE} (name, applied_at) VALUES (?, ?)",
            [name, datetime.now(timezone.utc).isoformat()],
        )

    @classmethod
    def run_migrations(cls, migrations_dir: str = "migrations"):
        """Run all pending migrations from a directory."""
        cls.init()
        migrations_path = Path(migrations_dir)

        if not migrations_path.exists():
            logger.info("No migrations directory found.")
            return

        migration_files = sorted(migrations_path.glob("*.py"))
        for mig_file in migration_files:
            name = mig_file.stem
            if not cls.is_applied(name):
                logger.info(f"Applying migration: {name}")
                # Execute migration file
                with open(mig_file) as f:
                    code = f.read()
                exec(compile(code, str(mig_file), "exec"), {"Database": Database})
                cls.mark_applied(name)
                logger.info(f"Migration applied: {name}")

    @classmethod
    def create_migration(cls, name: str, sql_up: str, sql_down: str = "", migrations_dir: str = "migrations"):
        """Create a new migration file."""
        migrations_path = Path(migrations_dir)
        migrations_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{name}.py"
        filepath = migrations_path / filename

        content = f'''"""
Migration: {name}
Created: {datetime.now().isoformat()}
"""

def up():
    Database.execute("""{sql_up}""")

def down():
    Database.execute("""{sql_down}""")

# Run migration
up()
'''
        with open(filepath, "w") as f:
            f.write(content)

        logger.info(f"Created migration: {filename}")
        return filepath
