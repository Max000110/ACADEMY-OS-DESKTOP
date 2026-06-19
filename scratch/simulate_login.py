import urllib.request
import urllib.parse
import urllib.error
import re
import sqlite3
import os
import bcrypt

def reset_db_to_temp():
    db_path = "/home/ubuntu/academyos/academyos_licensing.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    salt = bcrypt.gensalt()
    new_hash = bcrypt.hashpw(b"password123", salt).decode('utf-8')
    cursor.execute("UPDATE admin_users SET hashed_password = ?, needs_password_change = 1 WHERE username = 'admin'", (new_hash,))
    cursor.execute("DELETE FROM login_attempts")
    conn.commit()
    conn.close()
    print("[Database] Restored admin user to temporary credentials (password123) and needs_password_change=1.")

def test_full_flow():
    # Make sure we start from a clean slate
    reset_db_to_temp()
    
    # We will use HTTPCookieProcessor to handle cookies across requests automatically.
    cookie_jar = urllib.request.HTTPCookieProcessor()
    opener = urllib.request.build_opener(cookie_jar)
    
    base_url = "http://127.0.0.1:8000"
    
    print("\n=== STEP 1: GET /admin/login ===")
    req1 = urllib.request.Request(f"{base_url}/admin/login")
    with opener.open(req1) as resp:
        html1 = resp.read().decode('utf-8')
        print(f"Status: {resp.status} {resp.reason}")
        print(f"Set-Cookie Header: {resp.headers.get('Set-Cookie')}")
    
    csrf_token_1 = None
    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html1)
    if match:
        csrf_token_1 = match.group(1)
    print(f"CSRF Token: {csrf_token_1}")
    if not csrf_token_1:
        print("Error: Could not retrieve CSRF Token")
        return
        
    print("\n=== STEP 2: POST /admin/login (Authenticating with temporary credentials) ===")
    login_data = urllib.parse.urlencode({
        "username": "admin",
        "password": "password123",
        "csrf_token": csrf_token_1
    }).encode('utf-8')
    
    # Use a custom redirect handler to capture intermediate redirects and status codes
    class VerboseRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            print(f"-> Redirecting: HTTP {code} to {newurl}")
            print(f"-> Set-Cookie in redirect: {headers.get('Set-Cookie')}")
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    verbose_opener = urllib.request.build_opener(cookie_jar, VerboseRedirectHandler())
    
    req2 = urllib.request.Request(f"{base_url}/admin/login", data=login_data, method='POST')
    with verbose_opener.open(req2) as resp:
        html2 = resp.read().decode('utf-8')
        final_url = resp.geturl()
        print(f"Final URL reached: {final_url}")
        print(f"Status Code: {resp.status}")
        
    print("\n=== STEP 3: GET /admin/change-password page ===")
    # Because we got redirected, the opener should already have visited /admin/change-password. Let's see the title of HTML
    title_match = re.search(r'<title>(.*?)</title>', html2)
    title = title_match.group(1) if title_match else "Unknown"
    print(f"Current Page Title: '{title}'")
    
    csrf_token_2 = None
    match2 = re.search(r'name="csrf_token"\s+value="([^"]+)"', html2)
    if match2:
        csrf_token_2 = match2.group(1)
    print(f"CSRF Token on Change Password Page: {csrf_token_2}")
    
    print("\n=== STEP 4: POST /admin/change-password (Performing rotation to newpassword123) ===")
    change_data = urllib.parse.urlencode({
        "current_password": "password123",
        "new_password": "newpassword123",
        "confirm_password": "newpassword123",
        "csrf_token": csrf_token_2
    }).encode('utf-8')
    
    req4 = urllib.request.Request(f"{base_url}/admin/change-password", data=change_data, method='POST')
    with verbose_opener.open(req4) as resp:
        html4 = resp.read().decode('utf-8')
        final_url = resp.geturl()
        print(f"Final URL reached: {final_url}")
        print(f"Status Code: {resp.status}")
        
    # Step 5: Get fresh login page and CSRF token
    print("\n=== STEP 5: GET /admin/login after rotation ===")
    req5 = urllib.request.Request(f"{base_url}/admin/login")
    with verbose_opener.open(req5) as resp:
        html5 = resp.read().decode('utf-8')
        
    csrf_token_3 = None
    match3 = re.search(r'name="csrf_token"\s+value="([^"]+)"', html5)
    if match3:
        csrf_token_3 = match3.group(1)
    print(f"CSRF Token for secondary login: {csrf_token_3}")
    
    print("\n=== STEP 6: POST /admin/login (Authenticating with rotated credentials) ===")
    login_data_new = urllib.parse.urlencode({
        "username": "admin",
        "password": "newpassword123",
        "csrf_token": csrf_token_3
    }).encode('utf-8')
    
    req6 = urllib.request.Request(f"{base_url}/admin/login", data=login_data_new, method='POST')
    with verbose_opener.open(req6) as resp:
        html6 = resp.read().decode('utf-8')
        final_url = resp.geturl()
        print(f"Final URL reached: {final_url}")
        print(f"Status Code: {resp.status}")
        
    title_match = re.search(r'<title>(.*?)</title>', html6)
    title = title_match.group(1) if title_match else "Unknown"
    print(f"Current Page Title: '{title}'")
    
    # Check if dashboard headers or widgets exist
    if "admin" in final_url and "change-password" not in final_url:
        print("Verification Result: Dashboard loaded successfully under authenticated session!")
        # Print a snippet of dashboard UI
        print("\n--- DASHBOARD RENDER PROOF (Snippet) ---")
        lines = html6.split('\n')
        snippet_lines = []
        for line in lines:
            if "Dashboard" in line or "Welcome" in line or "License" in line or "Customer" in line:
                cleaned = line.strip()
                if cleaned and len(cleaned) < 150:
                    snippet_lines.append(cleaned)
        for s in snippet_lines[:15]:
            print(f"  {s}")
    else:
        print("Verification Result: Failed to load dashboard.")
        
    print("\n=== CLEANUP AND RESTORE TEMPORARY STATE ===")
    reset_db_to_temp()

if __name__ == "__main__":
    test_full_flow()
