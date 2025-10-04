"""
Database Migration Runner for ProviderHealth Table
Safely adds new columns with error handling for existing columns
"""

import sqlite3
import sys
from pathlib import Path

def run_migration(db_path: str = "llm_orchestrator.db"):
    """Run database migration with proper error handling"""
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Running migration on: {db_path}")
    
    # List of columns to add
    migrations = [
        ("response_time_ms", "ALTER TABLE provider_health ADD COLUMN response_time_ms REAL DEFAULT 0.0"),
        ("error_message", "ALTER TABLE provider_health ADD COLUMN error_message TEXT"),
        ("last_check", "ALTER TABLE provider_health ADD COLUMN last_check TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("consecutive_failures", "ALTER TABLE provider_health ADD COLUMN consecutive_failures INTEGER DEFAULT 0"),
        ("success_rate", "ALTER TABLE provider_health ADD COLUMN success_rate REAL DEFAULT 100.0"),
    ]
    
    # Execute each migration
    for column_name, sql in migrations:
        try:
            cursor.execute(sql)
            print(f"✓ Added column: {column_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"○ Column already exists: {column_name}")
            else:
                print(f"✗ Error adding column {column_name}: {e}")
                conn.rollback()
                conn.close()
                return False
    
    # Update existing records
    try:
        cursor.execute("""
            UPDATE provider_health
            SET 
                last_check = COALESCE(last_validated_at, CURRENT_TIMESTAMP),
                error_message = last_error,
                consecutive_failures = error_count
            WHERE last_check IS NULL OR last_check = ''
        """)
        print(f"✓ Updated {cursor.rowcount} existing records")
    except Exception as e:
        print(f"○ Update records (may be already updated): {e}")
    
    # Create index
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_health_last_check ON provider_health(last_check)")
        print("✓ Created index: idx_health_last_check")
    except Exception as e:
        print(f"○ Index creation: {e}")
    
    # Commit changes
    conn.commit()
    
    # Verify migration
    try:
        cursor.execute("""
            SELECT 
                provider_id,
                is_healthy,
                response_time_ms,
                last_check,
                consecutive_failures,
                success_rate
            FROM provider_health
            LIMIT 5
        """)
        rows = cursor.fetchall()
        print(f"\n✓ Migration successful! Verified {len(rows)} records")
        print("\nSample data:")
        for row in rows:
            print(f"  Provider {row[0]}: healthy={row[1]}, response_time={row[2]}ms")
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        conn.close()
        return False
    
    conn.close()
    return True

if __name__ == "__main__":
    # Get database path from command line or use default
    db_path = sys.argv[1] if len(sys.argv) > 1 else "llm_orchestrator.db"
    
    # Check if database exists
    if not Path(db_path).exists():
        print(f"Error: Database not found at {db_path}")
        sys.exit(1)
    
    # Run migration
    success = run_migration(db_path)
    sys.exit(0 if success else 1)