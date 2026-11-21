import json
import os
from pathlib import Path
import subprocess
import tempfile

from sqlalchemy import select

from app.models import DiscoveryInfo, TestCase
from app.db.database import utcnow

MODULES = ['Login', 'Home', 'Dashboard', 'Onboarding', 'Profiles', 'Transactions', 'Screening']


def bridge_environment(settings, folder):
    env = os.environ.copy()
    backend = str(Path(__file__).resolve().parents[2])
    env['PYTHONPATH'] = os.pathsep.join([backend, str(settings.automation_root), env.get('PYTHONPATH', '')])
    env['PYTEST_ADDOPTS'] = ''
    env.pop('SENTINEL_SELECTED', None)
    env.pop('SENTINEL_COLLECT', None)
    env['SENTINEL_METADATA'] = str(settings.metadata_file)
    env['SENTINEL_EVENTS'] = str(folder / 'events.jsonl')
    return env


def pytest_command(settings, workers=1):
    return [settings.automation_python, '-m', 'pytest', 'tests', '-p', 'app.services.pytest_bridge',
            '-o', 'addopts=', '-n', '0' if workers == 1 else str(workers), '-q']


def check_workers(settings, workers):
    if settings.executor == 'mock' or workers == 1:
        return
    result = subprocess.run(
        [settings.automation_python, '-c',
         'import importlib.util, sys; sys.exit(0 if importlib.util.find_spec("xdist") else 1)'],
        capture_output=True, timeout=15)
    if result.returncode != 0:
        raise ValueError('Multiple workers require pytest-xdist in the automation Python environment.')


def collect_tests(settings):
    if settings.executor == 'mock':
        records = []
        for module in MODULES:
            for category in ('Positive', 'Negative'):
                records.append(dict(pytest_node_id=f'mock::{module}::{category}', name=f'{module} {category.lower()} sample test',
                                    module=module, category=category, requires_real_camera=False, camera_classified=True))
        records.append(dict(pytest_node_id='mock::Onboarding::camera', name='Onboarding real-camera sample test',
                            module='Onboarding', category='Positive', requires_real_camera=True, camera_classified=True))
        return records, ['Mock inventory and execution are simulated, not real test results.']
    if not (settings.automation_root / 'tests').is_dir() or not Path(settings.automation_python).is_file():
        raise ValueError('Set AUTOMATION_ROOT and AUTOMATION_PYTHON to the automation project and its Python executable.')
    if not settings.metadata_file.is_file():
        raise ValueError('Test metadata file does not exist.')
    with tempfile.TemporaryDirectory(prefix='sentinel-collection-') as directory:
        folder = Path(directory)
        target = folder / 'collection.json'
        env = bridge_environment(settings, folder)
        env['SENTINEL_COLLECT'] = str(target)
        result = subprocess.run(pytest_command(settings) + ['--collect-only'], cwd=settings.automation_root,
                                env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
        if result.returncode not in (0, 5) or not target.is_file():
            raise ValueError('Pytest discovery failed. Existing inventory was preserved. Check the automation environment and collection errors.')
        payload = json.loads(target.read_text(encoding='utf-8'))
        if not payload.get('complete'):
            raise ValueError('Incomplete discovery. Existing inventory was preserved.')
        records = payload['tests']
    warnings = []
    if any(record['category'] == 'Unclassified' for record in records):
        warnings.append('Some tests have no explicit Positive/Negative classification. Happy Path requires classification in pytest markers or test_metadata.json.')
    if any(not record['camera_classified'] for record in records):
        warnings.append('Onboarding camera dependencies need explicit classification, including camera calls made by fixtures and helper methods.')
    return records, warnings


def sync_inventory(db, records, warnings, is_mock):
    # Only call after a successful full collection of tests/; never after a partial collection.
    nodes = [record['pytest_node_id'] for record in records]
    if len(nodes) != len(set(nodes)):
        raise ValueError('Discovery returned duplicate node IDs.')
    if any(record['category'] not in ('Positive', 'Negative', 'Unclassified') for record in records):
        raise ValueError('Metadata category must be Positive, Negative, or Unclassified.')
    existing = {case.pytest_node_id: case for case in db.scalars(select(TestCase).where(TestCase.is_mock == is_mock))}
    for record in records:
        case = existing.get(record['pytest_node_id'])
        if case is None:
            import uuid
            case = TestCase(case_code='NEW-' + uuid.uuid4().hex[:20], is_mock=is_mock, **record)
            db.add(case)
            db.flush()
            case.case_code = f'TC-{case.id:04d}'
        else:
            for key, value in record.items():
                setattr(case, key, value)
        case.is_active = True
    for node, case in existing.items():
        if node not in nodes:
            case.is_active = False
    info = db.get(DiscoveryInfo, 1)
    if info is None:
        info = DiscoveryInfo(id=1)
        db.add(info)
    info.discovered_at = utcnow()
    info.count = len(records)
    info.warnings = warnings
    db.commit()
    return info
