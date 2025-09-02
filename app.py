"""
Production entrypoint for Flask app on Render.
Reuses the Flask app instance from src/main.py
"""

import os

# Import the app object created in src/main.py
from src.main import app


if __name__ == "__main__":
    # Bind to 0.0.0.0, use PORT env var if set, default to 5000, and disable debug
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=False)