"""
PramaanX — Create an Atlas login user.
Run once:  python create_user.py
Requires:  pymongo, bcrypt (both already in requirements)
The MONGODB_URI in .env must be reachable.
"""
import os, sys
from pathlib import Path
from dotenv import load_dotenv

# Load the project .env
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

MONGODB_URI = os.getenv("MONGODB_URI", "")
MONGODB_DATABASE = os.getenv("MONGODB_DATABASE", "pramaanx")

if not MONGODB_URI:
    sys.exit("ERROR: MONGODB_URI is not set in .env")

try:
    import bcrypt
    from pymongo import MongoClient
except ImportError as e:
    sys.exit(f"ERROR: Missing package — {e}. Run: pip install pymongo bcrypt")

# ── Credentials — change these before running ──────────────────────────────────
OFFICER_EMAIL = os.getenv("OFFICER_EMAIL", "officer@pramaanx.dev")
OFFICER_PASSWORD = os.getenv("OFFICER_PASSWORD", "")
OFFICER_NAME = os.getenv("OFFICER_NAME", "Lead Officer")
OFFICER_ROLE = os.getenv("OFFICER_ROLE", "authorized_officer")
if not OFFICER_PASSWORD:
    sys.exit("ERROR: OFFICER_PASSWORD must be set in the environment")
# ──────────────────────────────────────────────────────────────────────────────

print(f"\n  Connecting to: {MONGODB_DATABASE} on Atlas…")
client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
db = client[MONGODB_DATABASE]

# Check if user already exists
existing = db.users.find_one({"email": OFFICER_EMAIL.strip().lower()})
if existing:
    print(f"\n  ✓ User already exists: {OFFICER_EMAIL}")
    print("  To reset the password, delete the document from Atlas and re-run.")
    client.close()
    sys.exit(0)

# Hash the password with bcrypt
salt = bcrypt.gensalt(rounds=12)
pw_hash = bcrypt.hashpw(OFFICER_PASSWORD.encode("utf-8"), salt).decode("utf-8")

user_doc = {
    "email": OFFICER_EMAIL.strip().lower(),
    "name": OFFICER_NAME,
    "role": OFFICER_ROLE,
    "password_hash": pw_hash,
    "active": True,
    "created_at": __import__("datetime").datetime.utcnow(),
    "last_login_at": None,
}

result = db.users.insert_one(user_doc)
client.close()

print(f"""
  ✓ User created successfully!

  ┌─────────────────────────────────────────────┐
  │  Officer ID (email):  {OFFICER_EMAIL:<24s}│
  │  Password:            (set from environment) │
  └─────────────────────────────────────────────┘

  Sign in at http://127.0.0.1:5173
  The "Officer ID" field on the login screen accepts your email.
""")
