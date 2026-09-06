"""Development entry point for Clinique Enhanced."""
import os

from app import app

if __name__ == '__main__':
    app.run(
        debug=os.environ.get('FLASK_DEBUG', '0') == '1',
        host='0.0.0.0',
        port=int(os.environ.get('PORT', '5000')),
    )
