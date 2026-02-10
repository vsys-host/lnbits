#!/usr/bin/env python3
"""
LNbits Setup Script
Creates a new user, authenticates, and retrieves the admin key.
"""

import os
import sys
import subprocess
import sqlite3

# Configuration
LOGIN_USERNAME = os.environ.get("LNBITS_ADMIN_USER")
LOGIN_PASSWORD = os.environ.get("LNBITS_ADMIN_PASSWORD")

# Validate required environment variables
if not LOGIN_USERNAME:
    print("Error: LNBITS_ADMIN_USER environment variable is not set")
    sys.exit(1)
if not LOGIN_PASSWORD:
    print("Error: LNBITS_ADMIN_PASSWORD environment variable is not set")
    sys.exit(1)

ADMIN_KEY_FILE = "/app/data/.lnbits_admin_key"
CLI_PATH = "/app/.venv/bin/lnbits-cli"
DB_PATH = "/app/data/database.sqlite3"


def migrate_db():
    """Run database migrations."""
    print(f"Step 0: Running database migrations...")

    try:
        cmd = [CLI_PATH, "db", "migrate"]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        print("Database migration completed successfully!")
        print(f"Output: {result.stdout}")
        return True

    except subprocess.CalledProcessError as e:
        print("Warning: Database migration failed")
        print(f"Error: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"Error: LNbits CLI not found at {CLI_PATH}")
        print("Make sure LNbits is properly installed")
        return False


def create_user():
    """Create a new LNbits user using CLI."""
    print(f"Step 1: Creating new LNbits user '{LOGIN_USERNAME}'...")

    try:
        cmd = [CLI_PATH, "users", "new", "-u", LOGIN_USERNAME, "-p", LOGIN_PASSWORD]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        print("User created successfully!")
        print(f"Output: {result.stdout}")
        return True

    except subprocess.CalledProcessError as e:
        print("Warning: User creation failed - user may already exist")
        print(f"Error: {e.stderr}")
        # Continue anyway - user might already exist
        return False
    except FileNotFoundError:
        print(f"Error: LNbits CLI not found at {CLI_PATH}")
        print("Make sure LNbits is properly installed")
        return False


def get_admin_key_from_db():
    """Get admin key from database using SQLite query."""
    print("\nStep 2: Getting admin key from database...")
    print(f"Database: {DB_PATH}")

    try:
        # Connect to SQLite database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Query to get admin key for the user
        query = """
            SELECT adminkey FROM wallets
            WHERE user IN (
                SELECT id FROM accounts
                WHERE username = ?
                LIMIT 1
            )
        """

        cursor.execute(query, (LOGIN_USERNAME,))
        result = cursor.fetchone()

        conn.close()

        if result and result[0]:
            admin_key = result[0]
            print(f"Admin key retrieved: {admin_key[:20]}...")
            return admin_key
        else:
            print(f"Error: No wallet found for user '{LOGIN_USERNAME}'")
            return None

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None


def save_admin_key(admin_key):
    """Save admin key to file."""
    print(f"\nStep 3: Saving admin key to {ADMIN_KEY_FILE}...")

    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(ADMIN_KEY_FILE), exist_ok=True)

        # Write admin key to file
        with open(ADMIN_KEY_FILE, "w") as f:
            f.write(admin_key)

        print("Admin key saved successfully!")
        return True

    except Exception as e:
        print(f"Error saving admin key: {e}")
        return False


def main():
    """Main execution flow."""
    print("=== LNbits Setup Script ===\n")

    # Check if admin key file already exists
    if os.path.exists(ADMIN_KEY_FILE):
        print(f"Admin key file already exists at {ADMIN_KEY_FILE}")
        print("Setup already completed. Exiting.")
        sys.exit(0)

    # Step 0: Migrate database
    migrate_db()

    # Step 1: Create user
    create_user()

    # Step 2: Get admin key from database
    admin_key = get_admin_key_from_db()
    if not admin_key:
        print("\nSetup failed: Could not retrieve admin key")
        sys.exit(1)

    # Step 3: Save admin key
    if not save_admin_key(admin_key):
        print("\nSetup failed: Could not save admin key")
        sys.exit(1)

    print("\n=== Setup completed successfully! ===")
    print(f"Admin key has been saved to {ADMIN_KEY_FILE}")


if __name__ == "__main__":
    main()
