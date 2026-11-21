import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

DASHBOARD_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(DASHBOARD_ROOT / '.env')


@dataclass
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv('DATABASE_URL', 'postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel_dashboard'))
    automation_root: Path = field(default_factory=lambda: Path(os.getenv('AUTOMATION_ROOT', str(DASHBOARD_ROOT.parent / 'testing'))).resolve())
    automation_python: str = field(default_factory=lambda: os.getenv('AUTOMATION_PYTHON', str(DASHBOARD_ROOT.parent / 'testing' / '.venv' / 'Scripts' / 'python.exe')))
    executor: str = field(default_factory=lambda: os.getenv('EXECUTION_PROVIDER', 'mock'))
    reports_root: Path = field(default_factory=lambda: DASHBOARD_ROOT / 'storage' / 'reports')
    allowed_origins: tuple = field(default_factory=lambda: tuple(os.getenv('FRONTEND_ORIGINS', 'http://127.0.0.1:5173,http://localhost:5173').split(',')))
    secure_cookies: bool = field(default_factory=lambda: os.getenv('SECURE_COOKIES', '0') == '1')
    camera_available: bool = field(default_factory=lambda: os.getenv('REAL_CAMERA_AVAILABLE', '0') == '1')
    metadata_file: Path = field(default_factory=lambda: DASHBOARD_ROOT / 'backend' / 'test_metadata.json')
    execution_timeout: int = 3600
    testing: bool = False

    def validate(self):
        if not self.testing and not self.database_url.startswith(('postgresql://', 'postgresql+psycopg://')):
            raise ValueError('Configure DATABASE_URL with a PostgreSQL connection. SQLite is reserved for automated tests.')
        if self.executor not in ('mock', 'pytest'):
            raise ValueError('EXECUTION_PROVIDER must be mock or pytest.')
