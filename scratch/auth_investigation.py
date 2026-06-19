import sqlite3
import os
import bcrypt
import datetime
import urllib.request
import urllib.parse
import re

def main():
    db_path = "/home/ubuntu/academyos/academyos_licensing.db"
    
    print("=== 1. DATABASE METADATA ===")
    print(f"Database File Path: {db_path}")
    print(f"Database File Size: {os.path.getsize(db_path)} bytes")
    print(f"Database Last Modified: {datetime.datetime.fromtimestamp(os.path.getmtime(db_path))}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("\n=== 2. QUERY ADMINUSER TABLE ===")
    # Query admin_users table
    cursor.execute("SELECT id, username, needs_password_change, hashed_password FROM admin_users")
    users = cursor.fetchall()
    for u in users:
        print(f"ID: {u[0]} | Username: {u[1]} | Needs Password Change: {u[2]} | Password Hash: {u[3]}")
        
    print("\n=== 3. DIRECT AUTHENTICATION TEST ===")
    test_username = "admin"
    test_password = "password123"
    
    cursor.execute("SELECT hashed_password, needs_password_change FROM admin_users WHERE username = ?", (test_username,))
    row = cursor.fetchone()
    if not row:
        print(f"User Lookup Result: USER NOT FOUND for username '{test_username}'")
    else:
        print(f"User Lookup Result: USER FOUND")
        hashed = row[0]
        needs_change = row[1]
        
        # Verify bcrypt
        bcrypt_result = bcrypt.checkpw(test_password.encode('utf-8'), hashed.encode('utf-8'))
        print(f"Bcrypt Verification Result (matches '{test_password}'): {bcrypt_result}")
        
        # Verify login logic
        auth_result = "SUCCESS" if bcrypt_result else "FAILED"
        print(f"Authentication Result: {auth_result}")
        if not bcrypt_result:
            print("Exact Reason: wrong bcrypt hash")
            
    print("\n=== 4. CHECK LOCKOUT SYSTEM ===")
    # Query login attempts
    cursor.execute("SELECT ip_address, username, timestamp, is_successful FROM login_attempts")
    attempts = cursor.fetchall()
    print(f"Total Login Attempts in Database: {len(attempts)}")
    for a in attempts:
        print(f"IP: {a[0]} | Username: {a[1]} | Timestamp: {a[2]} | Success: {a[3]}")
        
    # Check if locked
    ip_to_check = "152.58.29.133" # User's IP from the security audit log
    cursor.execute("""
        SELECT COUNT(*) FROM login_attempts 
        WHERE username = ? AND is_successful = 0 AND timestamp >= datetime('now', '-15 minutes')
    """, (test_username,))
    user_fail_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM login_attempts 
        WHERE ip_address = ? AND is_successful = 0 AND timestamp >= datetime('now', '-15 minutes')
    """, (ip_to_check,))
    ip_fail_count = cursor.fetchone()[0]
    
    print(f"Failed attempts for user '{test_username}' in last 15 mins: {user_fail_count}")
    print(f"Failed attempts for user IP '{ip_to_check}' in last 15 mins: {ip_fail_count}")
    
    is_locked = user_fail_count >= 5 or ip_fail_count >= 5
    print(f"Lockout Status: {'LOCKED' if is_locked else 'NOT LOCKED'}")
    
    conn.close()

if __name__ == "__main__":
    main()
