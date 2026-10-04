"""Create a deliberately failing, small project ZIP for the documented demo."""
from pathlib import Path
import zipfile

destination=Path(__file__).resolve().parents[1]/'docs'/'teamflow-demo.zip'
files={
    'backend/__init__.py':'',
    'backend/auth.py':'def valid_token(token):\n    # Demo exercise: accept the token "teamflow".\n    return False\n',
    'tests/test_auth.py':'from backend.auth import valid_token\n\ndef test_valid_token():\n    assert valid_token("teamflow") is True\n\ndef test_invalid_token():\n    assert valid_token("wrong") is False\n',
    'app.py':'from backend.auth import valid_token\nprint("TeamFlow demo: token accepted =", valid_token("teamflow"), flush=True)\n',
    'README.md':'# TeamFlow development-loop demo\n\nRun: python app.py\nTest: python -m pytest -q\n\nFix backend/auth.py to return token == "teamflow".\n',
}
with zipfile.ZipFile(destination,'w',zipfile.ZIP_DEFLATED) as archive:
    for path,content in files.items(): archive.writestr(path,content)
print(destination)
