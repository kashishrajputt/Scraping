import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS
from logger import logger


class DatabaseManager:
    
    def __init__(self):
        self.connection = None
        
    def connect(self):
        
        try:
            try:
                import psycopg
            except Exception as e:
                raise RuntimeError("psycopg is required for PostgreSQL. Install with 'pip install psycopg[binary]'") from e
            
            conn_str = (
                f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASS}"
            )
            self.connection = psycopg.connect(conn_str)
            # Use dict-like rows
            self.connection.autocommit = False
            logger.info(f" Connected to PostgreSQL database: {DB_NAME} @ {DB_HOST}:{DB_PORT}")
        except Exception as e:
            logger.error(f" Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
       
        if self.connection:
            self.connection.close()
            logger.info(" Database connection closed")
    
    def init_tables(self):
       
        try:
            cursor = self.connection.cursor()
            
            # Create cases table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS cases (
                    id BIGSERIAL PRIMARY KEY,
                    high_court TEXT NOT NULL,
                    bench TEXT NOT NULL,
                    case_number TEXT NOT NULL,
                    year INTEGER,
                    party_names TEXT,
                    status TEXT,
                    filing_date DATE,
                    last_hearing_date DATE,
                    judge_names TEXT,
                    pdf_link TEXT,
                    search_type TEXT NOT NULL,
                    search_query TEXT NOT NULL,
                    scraped_at TIMESTAMPTZ DEFAULT NOW(),
                    CONSTRAINT cases_unique UNIQUE (high_court, bench, case_number, search_type, search_query)
                )
                """
            )
            
            
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS search_logs (
                    id BIGSERIAL PRIMARY KEY,
                    high_court TEXT NOT NULL,
                    bench TEXT NOT NULL,
                    search_type TEXT NOT NULL,
                    search_query TEXT NOT NULL,
                    results_count INTEGER DEFAULT 0,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT,
                    executed_at TIMESTAMPTZ DEFAULT NOW()
                )
                """
            )
            
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_court_bench ON cases(high_court, bench)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_search ON cases(search_type, search_query)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_scraped_at ON cases(scraped_at)")

            self.connection.commit()
            logger.info(" PostgreSQL database tables initialized successfully")
            
        except Exception as e:
            logger.error(f" Failed to initialize database tables: {e}")
            raise
    
    def insert_case_record(self, record: Dict[str, Any]) -> bool:
        """Insert a case record into the PostgreSQL database"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute(
                """
                INSERT INTO cases (
                    high_court, bench, case_number, year, party_names, status,
                    filing_date, last_hearing_date, judge_names, pdf_link,
                    search_type, search_query
                ) VALUES (%(high_court)s, %(bench)s, %(case_number)s, %(year)s, %(party_names)s,
                        %(status)s, %(filing_date)s, %(last_hearing_date)s, %(judge_names)s,
                        %(pdf_link)s, %(search_type)s, %(search_query)s)
                    ON CONFLICT (high_court, bench, case_number, search_type, search_query) DO NOTHING;
                """, r
            )
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f" Failed to insert case record: {e}")
            return False
    
    def log_search(self, high_court: str, bench: str, search_type: str, 
                   search_query: str, results_count: int, success: bool = True, 
                   error_message: str = None) -> bool:
        """Log search operation"""
        try:
            cursor = self.connection.cursor()
            
            cursor.execute(
                """
                INSERT INTO search_logs (
                    high_court, bench, search_type, search_query,
                    results_count, success, error_message
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    high_court, bench, search_type, search_query,
                    results_count, success, error_message,
                ),
            )
            
            self.connection.commit()
            return True
            
        except Exception as e:
            logger.error(f" Failed to log search: {e}")
            return False
    
    def get_case_count(self) -> int:
        """Get total number of cases in database"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM cases")
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f" Failed to get case count: {e}")
            return 0
    
    def get_search_stats(self) -> Dict[str, Any]:
        """Get search statistics"""
        try:
            cursor = self.connection.cursor()
            
            # Total searches
            cursor.execute("SELECT COUNT(*) FROM search_logs")
            total_searches = cursor.fetchone()[0]
            
            # Successful searches
            cursor.execute("SELECT COUNT(*) FROM search_logs WHERE success = TRUE")
            successful_searches = cursor.fetchone()[0]
            
            # Total results
            cursor.execute("SELECT SUM(results_count) FROM search_logs WHERE success = TRUE")
            total_results = cursor.fetchone()[0] or 0
            
            # Recent searches (last 24 hours)
            cursor.execute(
                """
                SELECT COUNT(*) FROM search_logs 
                WHERE executed_at >= NOW() - INTERVAL '1 day'
                """
            )
            recent_searches = cursor.fetchone()[0]
            
            return {
                'total_searches': total_searches,
                'successful_searches': successful_searches,
                'failed_searches': total_searches - successful_searches,
                'total_results': total_results,
                'recent_searches': recent_searches,
                'success_rate': (successful_searches / total_searches * 100) if total_searches > 0 else 0
            }
            
        except Exception as e:
            logger.error(f" Failed to get search stats: {e}")
            return {}



_db_manager = None


def init_database() -> DatabaseManager:
    """Initialize the global PostgreSQL database manager"""
    global _db_manager
    
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.connect()
        _db_manager.init_tables()
    
    return _db_manager


def insert_case_record(record: Dict[str, Any]) -> bool:
    """Insert a case record using the global database manager"""
    global _db_manager
    
    if _db_manager is None:
        logger.warning(" Database not initialized, skipping record insertion")
        return False
    
    return _db_manager.insert_case_record(record)


def log_search(high_court: str, bench: str, search_type: str, 
               search_query: str, results_count: int, success: bool = True, 
               error_message: str = None) -> bool:
    """Log search operation using the global database manager"""
    global _db_manager
    
    if _db_manager is None:
        logger.warning(" Database not initialized, skipping search log")
        return False
    
    return _db_manager.log_search(high_court, bench, search_type, search_query, 
                                 results_count, success, error_message)


def get_database_stats() -> Dict[str, Any]:
    """Get database statistics"""
    global _db_manager
    
    if _db_manager is None:
        return {}
    
    stats = _db_manager.get_search_stats()
    stats['total_cases'] = _db_manager.get_case_count()
    
    return stats


def close_database():
    """Close the global database connection"""
    global _db_manager
    
    if _db_manager:
        _db_manager.disconnect()
        _db_manager = None

