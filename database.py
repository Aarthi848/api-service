# import pymysql
# from config import DB_CONFIG, PAYROLL_DB_CONFIG
# from logger import get_logger

# logger = get_logger("database")

# def get_connection(db_config: dict = None) -> pymysql.Connection:
#     if db_config is None:
#         db_config = DB_CONFIG  # Fallback to main DB

#     db_name = db_config.get("database", "unknown")
#     logger.debug(f"Creating database connection to: {db_name}")

#     try:
#         connection = pymysql.connect(
#             **db_config,
#             cursorclass=pymysql.cursors.DictCursor
#         )
#         logger.debug(f"Database connection successful: {db_name}")
#         return connection
#     except pymysql.MySQLError as e:
#         logger.error(f"MySQL connection failed ({db_name}): {e}")
#         raise
#     except Exception as e:
#         logger.error(f"Unexpected error connecting to {db_name}: {e}")
#         raise


import pymysql
from pymysql.cursors import DictCursor
from dbutils.pooled_db import PooledDB

from config import (
    DB_CONFIG,
    PAYROLL_DB_CONFIG,
    REPLICA_DB_CONFIG,
    REPLICATION_ENABLED
)
from logger import get_logger

logger = get_logger("database")

# ============================================================
# Connection Pools (All from .env via config.py)
# ============================================================

# Main DB Pool
main_pool = PooledDB(
    creator=pymysql,
    maxconnections=200,
    mincached=0,
    maxcached=50,
    blocking=True,
    ping=1,
    cursorclass=DictCursor,
    **DB_CONFIG
)

# Payroll DB Pool
payroll_pool = PooledDB(
    creator=pymysql,
    maxconnections=200,
    mincached=0,
    maxcached=50,
    blocking=True,
    ping=1,
    cursorclass=DictCursor,
    **PAYROLL_DB_CONFIG
)

# Replica DB Pool - Only created if replication is enabled
replica_pool = None
if REPLICATION_ENABLED:
    try:
        replica_pool = PooledDB(
            creator=pymysql,
            maxconnections=200,
            mincached=2,
            maxcached=50,
            blocking=True,
            ping=1,
            cursorclass=DictCursor,
            **REPLICA_DB_CONFIG
        )
        logger.info(f"✅ Replica pool created: {REPLICA_DB_CONFIG['host']}:{REPLICA_DB_CONFIG['port']}/{REPLICA_DB_CONFIG['database']}")
    except Exception as e:
        logger.warning(f"⚠️ Could not initialize replica pool: {e}")
else:
    logger.info("ℹ️ Replication disabled - no replica pool created")

# ============================================================
# Connection Functions
# ============================================================

def get_connection(db_config: dict = None) -> pymysql.Connection:
    """Get primary database connection from pool"""
    try:
        if db_config == PAYROLL_DB_CONFIG:
            return payroll_pool.connection()
        return main_pool.connection()
    except Exception as e:
        logger.exception("Database connection error")
        raise

def get_replica_connection() -> pymysql.Connection:
    """Get replica database connection from pool"""
    if not REPLICATION_ENABLED:
        raise RuntimeError("Replication is not enabled in .env")
    
    if replica_pool is None:
        raise RuntimeError("Replica connection pool is not initialized")
    
    try:
        return replica_pool.connection()
    except Exception as e:
        logger.exception("Replica database connection error")
        raise

def is_replication_enabled() -> bool:
    """Check if replication is enabled (from .env)"""
    return REPLICATION_ENABLED