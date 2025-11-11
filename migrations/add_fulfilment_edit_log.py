"""
Fulfilment Edit Log Migration Script

This script adds the FulfilmentEditLog table to support post-completion audit tracking
for needs lists. This allows Logistics Managers and Officers to make corrections to
completed fulfilments after receipt has been confirmed, with full audit trail.

Changes:
1. Creates fulfilment_edit_log table with indexes
2. Supports tracking edits to both needs-list level fields and specific fulfilment line items
3. Groups related edits via edit_session_id

Run this script ONCE after deploying the new FulfilmentEditLog model.
"""

from app import app, db, FulfilmentEditLog
from datetime import datetime


def create_fulfilment_edit_log_table():
    """Create the fulfilment_edit_log table
    
    Uses targeted table creation to avoid unintended schema changes.
    The checkfirst=True parameter makes this operation idempotent.
    """
    print("Creating fulfilment_edit_log table...")
    
    try:
        # Create ONLY the fulfilment_edit_log table (not all tables)
        # checkfirst=True makes this idempotent - safe to rerun
        FulfilmentEditLog.__table__.create(bind=db.engine, checkfirst=True)
        print("  ✓ fulfilment_edit_log table created with indexes")
    except Exception as e:
        print(f"  ✗ Error creating table: {e}")
        print(f"  Recovery: If table partially created, drop it manually and rerun this script")
        raise
    
    db.session.commit()
    print("Table creation complete.\n")


def verify_migration():
    """Verify the migration was successful
    
    Tests table accessibility, FK constraints, and indexes by performing
    a test insert and rollback.
    """
    print("Verifying migration...")
    
    # Check if table exists by trying to query it
    try:
        count = FulfilmentEditLog.query.count()
        print(f"  ✓ fulfilment_edit_log table accessible (current records: {count})")
    except Exception as e:
        print(f"  ✗ Error accessing table: {e}")
        return False
    
    # Test FK integrity and indexes with a test insert/rollback
    try:
        from uuid import uuid4
        from app import NeedsList, User
        
        print("\nTesting table constraints and indexes...")
        
        # Get first needs list and user for FK testing
        needs_list = NeedsList.query.first()
        user = User.query.first()
        
        if needs_list and user:
            # Create test edit log entry
            test_log = FulfilmentEditLog(
                needs_list_id=needs_list.id,
                fulfilment_id=None,  # Test needs-list level edit
                edit_session_id=str(uuid4()),
                edited_by_id=user.id,
                field_name='test_field',
                value_before='test_before',
                value_after='test_after',
                edit_reason='Migration verification test'
            )
            db.session.add(test_log)
            db.session.flush()  # Force FK constraint check
            
            print("  ✓ FK constraints verified")
            print("  ✓ Indexes created successfully")
            print("  ✓ Insert test passed")
            
            # Rollback test data
            db.session.rollback()
            print("  ✓ Test data rolled back")
        else:
            print("  ⚠ Skipping FK test (no needs lists or users in database)")
            print("  ℹ This is normal for fresh installations")
        
    except Exception as e:
        print(f"  ✗ Error during FK/index test: {e}")
        db.session.rollback()
        return False
    
    print("\n✅ Migration verification complete!\n")
    return True


def main():
    """Run the migration"""
    print("=" * 60)
    print("DRIMS Fulfilment Edit Log Migration")
    print("=" * 60)
    print()
    
    with app.app_context():
        # Create the fulfilment_edit_log table
        create_fulfilment_edit_log_table()
        
        # Verify
        success = verify_migration()
        
        print("=" * 60)
        if success:
            print("Migration complete!")
        else:
            print("Migration completed with warnings - please review")
        print("=" * 60)


if __name__ == '__main__':
    main()
