import os

# app.main builds a module-level app on import; keep its database in memory.
os.environ.setdefault("DATABASE_PATH", ":memory:")
