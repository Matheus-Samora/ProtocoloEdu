"""Separate runtime data and load only an explicitly selected settings file."""
import os
from pathlib import Path
from security.storage import atomic_write

def initialize_runtime():
    source = Path(__file__).resolve().parent.parent
    settings = os.environ.get('PROTOCOL_ENV_FILE')
    if settings:
        from dotenv import load_dotenv
        settings_path = Path(settings).resolve()
        if not settings_path.is_file():raise RuntimeError('Explicit settings file does not exist')
        os.environ['PROTOCOL_ENV_FILE'] = str(settings_path)
        load_dotenv(settings_path, override=False)
    directory = Path(os.environ.get('PROTOCOL_DATA_DIR') or str(source / 'private' / 'independent-runtime')).resolve()
    os.environ['PROTOCOL_DATA_DIR'] = str(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for name in ['criteria.json', 'document_catalog.json', 'courses_catalog.json']:
        target = directory / name
        if not target.exists():
            atomic_write(target, (source / name).read_bytes())
    os.chdir(directory)
    return directory
