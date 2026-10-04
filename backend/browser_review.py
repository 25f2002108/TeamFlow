"""Disposable browser QA server; never opens the user's development database."""
import os
from pathlib import Path
from app import create_app
from app.extensions import socketio

instance = Path(__file__).resolve().parent / 'instance'
app = create_app({'SQLALCHEMY_DATABASE_URI': 'sqlite:///phase-two-review.db', 'UPLOAD_FOLDER': str(instance / 'phase-two-review-uploads'), 'EXECUTION_MODE':'trusted-local'})
if __name__ == '__main__':
    socketio.run(app, host='127.0.0.1', port=int(os.getenv('PORT', '5001')), allow_unsafe_werkzeug=True)
