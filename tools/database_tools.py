"""Database interaction tools."""
import logging
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional, Union
from datetime import date, datetime
from schema import OfficerBio, ToolResult
from config import CONFIG
import json
import threading

logger = logging.getLogger(__name__)

# Thread-safe connection pool
_connection_pool = None
_pool_lock = threading.Lock()


def _get_connection_pool():
    """
    Get or create the connection pool.

    Returns:
        psycopg2.pool.ThreadedConnectionPool instance
    """
    global _connection_pool

    if _connection_pool is None:
        with _pool_lock:
            if _connection_pool is None:
                _connection_pool = pool.ThreadedConnectionPool(
                    minconn=1,
                    maxconn=10,
                    host=CONFIG.DB_HOST,
                    database=CONFIG.DB_NAME,
                    user=CONFIG.DB_USER,
                    password=CONFIG.DB_PASSWORD,
                    port=CONFIG.DB_PORT,
                    client_encoding='UTF8'  # Ensure UTF-8 for Chinese characters
                )

    return _connection_pool


def get_connection():
    """
    Get database connection from pool.

    Returns:
        psycopg2 connection object
    """
    try:
        pool_instance = _get_connection_pool()
        return pool_instance.getconn()
    except Exception as e:
        logger.warning(f"Connection pool failed, falling back to direct connection: {e}")
        return psycopg2.connect(
            host=CONFIG.DB_HOST,
            database=CONFIG.DB_NAME,
            user=CONFIG.DB_USER,
            password=CONFIG.DB_PASSWORD,
            port=CONFIG.DB_PORT,
            client_encoding='UTF8'
        )


def release_connection(conn):
    """
    Release connection back to pool.

    Args:
        conn: Connection to release
    """
    try:
        if _connection_pool is not None:
            _connection_pool.putconn(conn)
        else:
            conn.close()
    except Exception:
        conn.close()


def save_officer_bio_to_database(officer_bio: Union[OfficerBio, Dict[str, Any]]) -> Optional[int]:
    """
    Save OfficerBio data to pla_leaders table.

    Args:
        officer_bio: OfficerBio instance or dictionary with officer data

    Returns:
        Record ID or None on failure
    """
    # Normalize to dict
    if isinstance(officer_bio, OfficerBio):
        bio_dict = officer_bio.to_dict(exclude_none=True)
    else:
        bio_dict = officer_bio

    conn = get_connection()
    cursor = conn.cursor()
    try:
        query = """
        INSERT INTO pla_leaders (
            full_name, name_pinyin, birth_date, death_date,
            birth_place, data
        ) VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (full_name) DO UPDATE SET
            name_pinyin = EXCLUDED.name_pinyin,
            birth_date = EXCLUDED.birth_date,
            death_date = EXCLUDED.death_date,
            birth_place = EXCLUDED.birth_place,
            data = EXCLUDED.data,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
        """
        cursor.execute(query, (
            bio_dict.get('name'),
            bio_dict.get('pinyin_name'),
            bio_dict.get('birth_date'),
            bio_dict.get('death_date'),
            bio_dict.get('hometown'),
            json.dumps(bio_dict, ensure_ascii=False, default=str),
        ))
        record_id = cursor.fetchone()[0]
        conn.commit()
        logger.info(f"Saved officer bio to database with ID {record_id}")
        return record_id
    except Exception as e:
        conn.rollback()
        logger.warning(f"Could not save officer bio to database: {e}")
        return None
    finally:
        cursor.close()
        release_connection(conn)


def initialize_database():
    """
    Initialize database schema if it doesn't exist.
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pla_leaders (
            id SERIAL PRIMARY KEY,
            full_name VARCHAR(255) NOT NULL UNIQUE,
            name_pinyin VARCHAR(255),
            birth_date TEXT,
            death_date TEXT,
            birth_place VARCHAR(255),
            data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Create indexes
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pla_leaders_name
        ON pla_leaders(full_name)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_pla_leaders_birth_date
        ON pla_leaders(birth_date)
        """)

        # Create units table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS units (
            unit_id SERIAL PRIMARY KEY,
            unit_name VARCHAR(255) NOT NULL,
            unit_type VARCHAR(100),
            parent_unit_id INTEGER REFERENCES units(unit_id),
            theater_command VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Create index for unit name lookup
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_units_name
        ON units(unit_name)
        """)

        conn.commit()

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        release_connection(conn)


# Anthropic tool definition for officer lookup
LOOKUP_OFFICER_TOOL = {
    "name": "lookup_existing_officer",
    "description": "Search database for existing officer by name. Returns officer data if found, prevents duplicates.",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Chinese name of the officer to search for"
            }
        },
        "required": ["name"]
    }
}


def execute_lookup_officer(tool_input: Dict[str, Any]) -> ToolResult:
    """
    Execute officer lookup tool to search database for existing records.

    This function queries the PostgreSQL database for an officer by name,
    returning existing data if found or confirming absence if not found.

    Args:
        tool_input: Dictionary containing:
            - name: str - Chinese name of the officer

    Returns:
        ToolResult with:
        - success=True if query succeeded (even if no officer found)
        - data contains officer info if found, or indication of not found
        - success=False only on database errors

    Example:
        >>> tool_input = {"name": "林炳尧"}
        >>> result = execute_lookup_officer(tool_input)
        >>> if result.success and result.data.get('found'):
        ...     officer = result.data['officer']
        ...     print(f"Found existing officer: {officer['full_name']}")

    Notes:
        - Uses connection pooling for efficiency
        - Handles Chinese characters with UTF-8 encoding
        - Performs exact name match
        - Returns all officer data including JSONB field
    """
    name = tool_input.get('name')

    if not name:
        return ToolResult(
            tool_name="lookup_existing_officer",
            success=False,
            error="Officer name is required"
        )

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Query for exact name match
        query = """
        SELECT
            id,
            full_name,
            name_pinyin,
            birth_date,
            death_date,
            birth_place,
            data,
            created_at,
            updated_at
        FROM pla_leaders
        WHERE full_name = %s
        LIMIT 1
        """

        cursor.execute(query, (name,))
        result = cursor.fetchone()

        cursor.close()

        if result:
            # Officer found
            officer_data = dict(result)

            def _to_serializable_date(value: Any) -> Any:
                if isinstance(value, (datetime, date)):
                    return value.isoformat()
                return value

            # Normalize date-like values for JSON serialization.
            officer_data['birth_date'] = _to_serializable_date(officer_data.get('birth_date'))
            officer_data['death_date'] = _to_serializable_date(officer_data.get('death_date'))
            officer_data['created_at'] = _to_serializable_date(officer_data.get('created_at'))
            officer_data['updated_at'] = _to_serializable_date(officer_data.get('updated_at'))

            return ToolResult(
                tool_name="lookup_existing_officer",
                success=True,
                data={
                    "found": True,
                    "officer": officer_data,
                    "message": f"Found existing record for {name}"
                }
            )
        else:
            # Officer not found
            return ToolResult(
                tool_name="lookup_existing_officer",
                success=True,
                data={
                    "found": False,
                    "message": f"No existing record found for {name}"
                }
            )

    except psycopg2.Error as e:
        return ToolResult(
            tool_name="lookup_existing_officer",
            success=False,
            data={"name": name},
            error=f"Database error: {str(e)}"
        )

    except Exception as e:
        return ToolResult(
            tool_name="lookup_existing_officer",
            success=False,
            data={"name": name},
            error=f"Unexpected error: {str(e)}"
        )

    finally:
        if conn:
            release_connection(conn)


# Anthropic tool definition for unit lookup
LOOKUP_UNIT_TOOL = {
    "name": "lookup_unit_by_name",
    "description": "Look up PLA unit by name to get unit_id. Supports fuzzy matching for unit name variations.",
    "input_schema": {
        "type": "object",
        "properties": {
            "unit_name": {
                "type": "string",
                "description": "Name of the PLA unit to search for (Chinese or English)"
            }
        },
        "required": ["unit_name"]
    }
}


def execute_lookup_unit(tool_input: Dict[str, Any]) -> ToolResult:
    """
    Execute unit lookup tool to search database for PLA units.

    This function queries the units table for a matching unit name,
    supporting both exact and fuzzy matching for variations in naming.

    Args:
        tool_input: Dictionary containing:
            - unit_name: str - Name of the unit to search for

    Returns:
        ToolResult with:
        - success=True if query succeeded
        - data contains unit info if found
        - success=False on database errors

    Example:
        >>> tool_input = {"unit_name": "南京军区"}
        >>> result = execute_lookup_unit(tool_input)
        >>> if result.success and result.data.get('found'):
        ...     unit = result.data['unit']
        ...     print(f"Unit ID: {unit['unit_id']}")

    Notes:
        - Uses fuzzy matching with LIKE for flexibility
        - Handles Chinese characters with UTF-8 encoding
        - Returns unit_id and metadata
        - Returns best match if multiple units match
    """
    unit_name = tool_input.get('unit_name')

    if not unit_name:
        return ToolResult(
            tool_name="lookup_unit_by_name",
            success=False,
            error="Unit name is required"
        )

    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # First try exact match
        exact_query = """
        SELECT
            unit_id,
            unit_name,
            unit_type,
            parent_unit_id,
            theater_command,
            created_at
        FROM units
        WHERE unit_name = %s
        LIMIT 1
        """

        cursor.execute(exact_query, (unit_name,))
        result = cursor.fetchone()

        # If no exact match, try fuzzy match
        if not result:
            fuzzy_query = """
            SELECT
                unit_id,
                unit_name,
                unit_type,
                parent_unit_id,
                theater_command,
                created_at,
                similarity(unit_name, %s) as match_score
            FROM units
            WHERE unit_name ILIKE %s
            ORDER BY similarity(unit_name, %s) DESC
            LIMIT 1
            """

            escaped = unit_name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            fuzzy_pattern = f"%{escaped}%"
            try:
                # Try with pg_trgm similarity if available
                cursor.execute(fuzzy_query, (unit_name, fuzzy_pattern, unit_name))
                result = cursor.fetchone()
            except psycopg2.Error:
                conn.rollback()
                # Fallback to simple ILIKE without similarity scoring
                simple_query = """
                SELECT
                    unit_id,
                    unit_name,
                    unit_type,
                    parent_unit_id,
                    theater_command,
                    created_at
                FROM units
                WHERE unit_name ILIKE %s
                LIMIT 1
                """
                cursor.execute(simple_query, (fuzzy_pattern,))
                result = cursor.fetchone()

        cursor.close()

        if result:
            # Unit found
            unit_data = dict(result)

            # Convert dates to strings
            if unit_data.get('created_at'):
                unit_data['created_at'] = unit_data['created_at'].isoformat()

            # Remove match_score from output if present
            unit_data.pop('match_score', None)

            return ToolResult(
                tool_name="lookup_unit_by_name",
                success=True,
                data={
                    "found": True,
                    "unit": unit_data,
                    "message": f"Found unit: {unit_data['unit_name']} (ID: {unit_data['unit_id']})"
                }
            )
        else:
            # Unit not found
            return ToolResult(
                tool_name="lookup_unit_by_name",
                success=True,
                data={
                    "found": False,
                    "message": f"No unit found matching '{unit_name}'"
                }
            )

    except psycopg2.Error as e:
        return ToolResult(
            tool_name="lookup_unit_by_name",
            success=False,
            data={"unit_name": unit_name},
            error=f"Database error: {str(e)}"
        )

    except Exception as e:
        return ToolResult(
            tool_name="lookup_unit_by_name",
            success=False,
            data={"unit_name": unit_name},
            error=f"Unexpected error: {str(e)}"
        )

    finally:
        if conn:
            release_connection(conn)


# Anthropic tool definition for saving officer bio to database
SAVE_TO_DATABASE_TOOL = {
    "name": "save_to_database",
    "description": "Persist officer bio to PostgreSQL. Call after save_officer_bio and validation.",
    "input_schema": {
        "type": "object",
        "properties": {
            "officer_bio": {
                "type": "object",
                "description": "The OfficerBio object returned from save_officer_bio"
            }
        },
        "required": ["officer_bio"]
    }
}


def execute_save_to_database(tool_input: Dict[str, Any]) -> ToolResult:
    """
    Execute save_to_database tool to persist OfficerBio to PostgreSQL.

    Delegates to save_officer_bio_to_database for the actual DB write.

    Args:
        tool_input: Dictionary containing:
            - officer_bio: dict - OfficerBio data to save

    Returns:
        ToolResult with:
        - success=True if save succeeded, with database ID in data
        - success=False on errors
    """
    officer_bio_dict = tool_input.get('officer_bio')

    if not officer_bio_dict:
        return ToolResult(
            tool_name="save_to_database",
            success=False,
            error="officer_bio is required"
        )

    if not officer_bio_dict.get('name'):
        return ToolResult(
            tool_name="save_to_database",
            success=False,
            error="officer_bio.name is required"
        )

    record_id = save_officer_bio_to_database(officer_bio_dict)

    if record_id is not None:
        return ToolResult(
            tool_name="save_to_database",
            success=True,
            data={
                "id": record_id,
                "name": officer_bio_dict.get('name'),
                "message": f"Successfully saved officer bio to database with ID {record_id}"
            }
        )
    else:
        return ToolResult(
            tool_name="save_to_database",
            success=False,
            data={"name": officer_bio_dict.get('name')},
            error="Database save failed (check logs for details)"
        )
