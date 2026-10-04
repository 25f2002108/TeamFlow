import secrets
from ..models import Team
from ..extensions import db

def generate_code():
    alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    while True:
        code = 'TF-' + ''.join(secrets.choice(alphabet) for _ in range(6))
        if not db.session.scalar(db.select(Team).filter_by(team_code=code)):
            return code
