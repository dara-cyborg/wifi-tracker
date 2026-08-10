import os

from itsdangerous import URLSafeTimedSerializer

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable not set")

serializer = URLSafeTimedSerializer(SECRET_KEY)
SESSION_COOKIE_MAX_AGE = 8 * 60 * 60
