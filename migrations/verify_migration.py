"""
Verify database migration status
Check if all required ProviderHealth columns exist
"""

import sqlite3
import sys
from pathlib import Path

def verify_migration(db_path: str = "llm_orchestrator.db"):
    """Verify that all required columns exist in provider_health table"""
    
    if not Path(db_path).exists():
        print(f"❌ Database not found: {db_path}")
        return False
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Checking database: {db_path}")
    print("=" * 60)
    
    # Get table structure
    cursor.execute("PRAGMA table_info(provider_health)")
    columns = {row[1]: row[2] for row in cursor.fetchall()}
    
    # Required columns
    required = {
        'id': 'INTEGER',
        'provider_id': 'INTEGER',
        'is_healthy': 'BOOLEAN',
        'response_time_ms': 'REAL',
        'error_message': 'TEXT',
        'last_check': 'TIMESTAMP',
        'consecutive_failures': 'INTEGER',
        'success_rate': 'REAL',
    }
    
    # Check each required column
    missing = []
    present = []
    
    for col_name, col_type in required.items():
        if col_name in columns:
            present.append(col_name)
            status = "✓"
        else:
            missing.append(col_name)
            status = "✗"
        
        actual_type = columns.get(col_name, 'MISSING')
        print(f"{status} {col_name:25} {actual_type}")
    
    print("=" * 60)
    
    # Summary
    if missing:
        print(f"\n❌ Migration incomplete: {len(missing)} columns missing")
        print(f"Missing columns: {', '.join(missing)}")
        print("\nPlease run: migrations\\run_migration.bat")
        conn.close()
        return False
    else:
        print(f"\n✅ Migration complete: All {len(present)} required columns exist")
        
        # Show sample data
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
                LIMIT 3
            """)
            rows = cursor.fetchall()
            
            if rows:
                print(f"\nSample data ({len(rows)} records):")
                print("-" * 60)
                for row in rows:
                    print(f"Provider {row[0]}: healthy={row[1]}, "
                          f"response_time={row[2]:.1f}ms, "
                          f"success_rate={row[5]:.1f}%")
            else:
                print("\nℹ No health records yet (will be created automatically)")
        except Exception as e:
            print(f"\nℹ Sample data query failed: {e}")
        
        conn.close()
        return True

if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "llm_orchestrator.db"
    success = verify_migration(db_path)
    sys.exit(0 if success else 1)