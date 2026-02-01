"""
Database migration script to fix timezone-aware datetime for API tokens

This script adds timezone info to all naive datetime fields in the api_tokens table.
"""

from app.core.database import SessionLocal
from app.models.api_token import ApiToken
from datetime import timezone
import sys

def fix_token_timezones():
    """Fix timezone-aware datetime for all tokens"""
    db = SessionLocal()
    try:
        tokens = db.query(ApiToken).all()
        print(f"Found {len(tokens)} tokens to update...")

        # Use raw SQL to update datetime fields with timezone
        from sqlalchemy import text

        # Update expires_at - add UTC timezone
        result = db.execute(text("""
            UPDATE api_tokens
            SET expires_at = TIMESTAMP(CONVERT_TZ(expires_at, 'UTC', 'UTC'))
            WHERE expires_at IS NOT NULL
            AND DATE(expires_at) >= '2026-01-01'
        """))
        print(f"Updated expires_at for {result.rowcount} tokens")

        # Update created_at - add UTC timezone
        result = db.execute(text("""
            UPDATE api_tokens
            SET created_at = TIMESTAMP(CONVERT_TZ(created_at, 'UTC', 'UTC'))
            WHERE created_at IS NOT NULL
        """))
        print(f"Updated created_at for {result.rowcount} tokens")

        # Update last_used_at - add UTC timezone
        result = db.execute(text("""
            UPDATE api_tokens
            SET last_used_at = TIMESTAMP(CONVERT_TZ(last_used_at, 'UTC', 'UTC'))
            WHERE last_used_at IS NOT NULL
        """))
        print(f"Updated last_used_at for {result.rowcount} tokens")

        # Update revoked_at - add UTC timezone
        result = db.execute(text("""
            UPDATE api_tokens
            SET revoked_at = TIMESTAMP(CONVERT_TZ(revoked_at, 'UTC', 'UTC'))
            WHERE revoked_at IS NOT NULL
        """))
        print(f"Updated revoked_at for {result.rowcount} tokens")

        db.commit()
        print("\nTimezone migration completed successfully!")

        # Verify the update
        print("\nVerifying timezone update...")
        db.expire_all()
        tokens = db.query(ApiToken).all()
        for token in tokens[:5]:  # Check first 5 tokens
            print(f"\nToken {token.id}:")
            print(f"  expires_at: {token.expires_at}")
            print(f"  expires_at.tzinfo: {token.expires_at.tzinfo}")

    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting timezone migration for API tokens...")
    fix_token_timezones()
    print("Done!")
