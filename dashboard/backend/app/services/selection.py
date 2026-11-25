"""Use the same test selection for run previews and execution."""
import os

from sqlalchemy import select

from app.models import TestCase


def selected_cases(db, settings, options):
    query = select(TestCase).where(TestCase.is_active.is_(True), TestCase.is_mock == (settings.executor == 'mock'))
    if options.scope_type == 'module':
        if not options.scope_value:
            raise ValueError('Select a module.')
        query = query.where(TestCase.module == options.scope_value)
    elif options.scope_type == 'test':
        query = query.where(TestCase.case_code == options.scope_value)
    elif options.scope_value:
        raise ValueError('All Systems cannot specify an individual module.')
    cases = list(db.scalars(query.order_by(TestCase.id)))
    if not cases:
        raise ValueError('No active tests exist in this scope. Sync Tests first.')
    if options.selection != 'all':
        if any(case.category == 'Unclassified' for case in cases):
            raise ValueError('Classify tests as Positive/Negative before using this selection. Update test_metadata.json or pytest markers.')
        cases = [case for case in cases if case.category == options.selection.title()]
    if options.camera_mode != 'include' and any(not case.camera_classified for case in cases):
        raise ValueError('Classify real-camera dependencies before filtering this scope. Helpers and fixtures may also require a camera.')
    if options.camera_mode == 'exclude':
        cases = [case for case in cases if not case.requires_real_camera]
    elif options.camera_mode == 'only':
        cases = [case for case in cases if case.requires_real_camera]
    if not cases:
        raise ValueError('No tests match the selected settings.')
    return cases


def worker_recommendation(cases):
    count = len(cases)
    camera = any(case.requires_real_camera or not case.camera_classified for case in cases)
    # A starting estimate, not a benchmark: about 20 tests per worker, at most
    # 8 workers, capped by the execution machine's reported CPU count.
    workers = 1 if camera else min((count + 19) // 20, os.cpu_count() or 1, 8, count)
    reason = ('Use one worker because this selection may share a real camera.' if camera
              else 'Starting estimate: about 20 tests per worker, capped at 8 and the execution machine CPU count. Reduce workers if tests share accounts or data.')
    return dict(selectedCount=count, recommendedWorkers=workers, reason=reason)
