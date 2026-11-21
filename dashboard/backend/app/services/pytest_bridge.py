"""Loaded in the AUTOMATION Python environment; never edits the test project."""
import importlib.util
import json
import os
from pathlib import Path

import pytest

items_seen = []


def pytest_addoption(parser):
    # Support strict sequential mode even if the automation venv has no xdist.
    if importlib.util.find_spec('xdist') is None:
        parser.getgroup('sentinel')._addoption('-n', dest='numprocesses', type=int, choices=[0], default=0)


def pytest_collection_modifyitems(config, items):
    global items_seen
    overrides = json.loads(Path(os.environ['SENTINEL_METADATA']).read_text(encoding='utf-8'))
    records = []
    for item in items:
        node = item.nodeid
        marks = {mark.name for mark in item.iter_markers()}
        filename = node.split('::')[0].replace('\\', '/').lower()
        if '/profiles/' in filename:
            module = 'Profiles'
        elif 'onboarding' in filename or 'entity_sections' in filename or 'entity_documents' in filename or 'client_reuse' in filename:
            module = 'Onboarding'
        elif 'transaction' in filename:
            module = 'Transactions'
        elif 'screening' in filename:
            module = 'Screening'
        elif 'dashboard' in filename:
            module = 'Dashboard'
        elif 'login' in filename:
            module = 'Login'
        elif 'home' in filename:
            module = 'Home'
        else:
            module = Path(filename).stem.removeprefix('test_').replace('_', ' ').title()
        category = 'Unclassified'
        if marks & {'positive', 'happy_path'}:
            category = 'Positive'
        elif 'negative' in marks or (getattr(item, 'originalname', None) or item.name).startswith('test_negative_'):
            category = 'Negative'
        camera = 'real_camera' in marks
        record = dict(pytest_node_id=node, name=item.name, module=module, category=category,
                      requires_real_camera=camera, camera_classified=camera or module != 'Onboarding')
        override = overrides.get(node, {})
        for field in ('module', 'category', 'requires_real_camera'):
            if field in override:
                record[field] = override[field]
        if 'requires_real_camera' in override:
            record['camera_classified'] = True
        records.append(record)
    items_seen = records
    selected_path = os.getenv('SENTINEL_SELECTED')
    if selected_path:
        selected = set(json.loads(Path(selected_path).read_text(encoding='utf-8')))
        rejected = [item for item in items if item.nodeid not in selected]
        items[:] = [item for item in items if item.nodeid in selected]
        config.hook.pytest_deselected(items=rejected)


def write_event(record):
    with Path(os.environ['SENTINEL_EVENTS']).open('a', encoding='utf-8') as file:
        file.write(json.dumps(record) + '\n')


def pytest_runtest_logreport(report):
    # xdist forwards worker reports to the controller. Only the controller writes
    # events, avoiding concurrent file writes and duplicate phase results.
    if os.getenv('PYTEST_XDIST_WORKER'):
        return
    # Emit phases, not just call outcomes: teardown errors must override a pass.
    write_event(dict(node=report.nodeid, phase=report.when, outcome=report.outcome,
                     duration=report.duration, message=str(report.longrepr) if report.longrepr else None,
                     xfail=hasattr(report, 'wasxfail')))


def pytest_sessionfinish(session, exitstatus):
    if os.getenv('SENTINEL_COLLECT'):
        Path(os.environ['SENTINEL_COLLECT']).write_text(
            json.dumps({'complete': int(exitstatus) in (0, 5), 'tests': items_seen}), encoding='utf-8')
