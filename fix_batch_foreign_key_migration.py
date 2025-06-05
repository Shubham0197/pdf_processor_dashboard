#!/usr/bin/env python3
"""
Migration script to fix the foreign key constraint between processing_jobs and batch_jobs.

The issue is that batch_jobs.id is CHAR(36) but processing_jobs.batch_id is INTEGER,
which creates a type mismatch in the foreign key constraint.
"""

import sqlite3
import os

def fix_foreign_key_constraint():
    """Fix the foreign key constraint by updating the processing_jobs table"""
    
    db_path = "pdf_processing.db"
    if not os.path.exists(db_path):
        print(f"❌ Database file {db_path} not found")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔍 Checking current schema...")
        
        # Check current processing_jobs schema
        cursor.execute("PRAGMA table_info(processing_jobs)")
        columns = cursor.fetchall()
        print("Current processing_jobs columns:")
        for col in columns:
            print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
        
        # Check if we need to fix the batch_id column type
        batch_id_column = next((col for col in columns if col[1] == 'batch_id'), None)
        if batch_id_column and 'INTEGER' in batch_id_column[2]:
            print("🔧 Need to fix batch_id column type from INTEGER to VARCHAR(36)")
            
            # Step 1: Disable foreign key constraints temporarily
            cursor.execute("PRAGMA foreign_keys = OFF")
            
            # Step 2: Create a new table with the correct schema
            cursor.execute("""
                CREATE TABLE processing_jobs_new (
                    id INTEGER NOT NULL, 
                    job_id VARCHAR(36), 
                    batch_id VARCHAR(36), 
                    file_url VARCHAR(255) NOT NULL, 
                    file_name VARCHAR(255), 
                    status VARCHAR(20), 
                    created_at DATETIME DEFAULT (CURRENT_TIMESTAMP), 
                    updated_at DATETIME, 
                    completed_at DATETIME, 
                    error_message TEXT, 
                    processing_time INTEGER, 
                    extracted_text TEXT, 
                    doc_metadata JSON, 
                    "references" JSON, 
                    webhook_sent BOOLEAN, 
                    webhook_response JSON, 
                    progress_percentage INTEGER DEFAULT 0, 
                    started_at TIMESTAMP, 
                    estimated_completion TIMESTAMP, 
                    worker_id VARCHAR(255), 
                    last_heartbeat TIMESTAMP,
                    PRIMARY KEY (id), 
                    FOREIGN KEY(batch_id) REFERENCES batch_jobs (id)
                )
            """)
            
            # Step 3: Copy data from old table to new table
            cursor.execute("""
                INSERT INTO processing_jobs_new 
                SELECT * FROM processing_jobs
            """)
            
            # Step 4: Drop the old table
            cursor.execute("DROP TABLE processing_jobs")
            
            # Step 5: Rename the new table
            cursor.execute("ALTER TABLE processing_jobs_new RENAME TO processing_jobs")
            
            # Step 6: Recreate indexes
            cursor.execute("CREATE UNIQUE INDEX ix_processing_jobs_job_id ON processing_jobs (job_id)")
            cursor.execute("CREATE INDEX ix_processing_jobs_id ON processing_jobs (id)")
            
            # Step 7: Re-enable foreign key constraints
            cursor.execute("PRAGMA foreign_keys = ON")
            
            # Step 8: Verify the foreign key constraint
            cursor.execute("PRAGMA foreign_key_check(processing_jobs)")
            fk_violations = cursor.fetchall()
            if fk_violations:
                print(f"⚠️  Foreign key violations found: {fk_violations}")
            else:
                print("✅ Foreign key constraints are valid")
            
            conn.commit()
            print("✅ Successfully fixed batch_id column type and foreign key constraint")
        else:
            print("✅ batch_id column type is already correct")
        
        # Verify the final schema
        cursor.execute("PRAGMA table_info(processing_jobs)")
        columns = cursor.fetchall()
        print("\nFinal processing_jobs columns:")
        for col in columns:
            print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error fixing foreign key constraint: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("🔧 Fixing foreign key constraint between processing_jobs and batch_jobs...")
    success = fix_foreign_key_constraint()
    if success:
        print("✅ Migration completed successfully!")
    else:
        print("❌ Migration failed!") 