"""Run all 18 assignment tests, or --group unit / component.

Results are generated from assertions, never supplied as expected output.
"""
import argparse
import importlib.metadata
import json
import os
import platform
import socket
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument('--group', choices=['all', 'unit', 'component'], default='all')
args = parser.parse_args()
os.environ['DJANGO_SETTINGS_MODULE'] = 'tests_a4.settings'
import django
django.setup()
from django.conf import settings
from django.test.runner import DiscoverRunner

assert settings.DATABASES['default']['NAME'] == ':memory:'
assert settings.DATABASES['default']['TEST']['NAME'] == ':memory:'
records = []

class Result(unittest.TextTestResult):
    def getDescription(self, test):
        return test._testMethodName
    def startTest(self, test):
        self.outcome = 'ERROR'
        self.detail = ''
        super().startTest(test)
    def addSuccess(self, test):
        self.outcome = 'PASS'
        super().addSuccess(test)
    def addFailure(self, test, err):
        self.outcome = 'FAIL'
        self.detail = self._exc_info_to_string(err, test)
        super().addFailure(test, err)
    def addError(self, test, err):
        self.outcome = 'ERROR'
        self.detail = self._exc_info_to_string(err, test)
        super().addError(test, err)
    def addSkip(self, test, reason):
        self.outcome = 'SKIP'
        self.detail = reason
        super().addSkip(test, reason)
    def stopTest(self, test):
        records.append({'test': test.id(), 'status': self.outcome,
                        'actual': getattr(test, 'actual', 'No observation recorded'),
                        'detail': self.detail})
        super().stopTest(test)

class TextRunner(unittest.TextTestRunner):
    resultclass = Result

class Runner(DiscoverRunner):
    test_runner = TextRunner
    def setup_databases(self, **kwargs):
        # Keep evidence screenshots readable; real migrations still execute.
        verbosity = self.verbosity
        self.verbosity = 0
        try:
            return super().setup_databases(**kwargs)
        finally:
            self.verbosity = verbosity

labels = ['tests_a4'] if args.group == 'all' else ['tests_a4.test_' + args.group]
print('AnyAccess Assignment 4 | group=' + args.group, flush=True)
print('Python ' + platform.python_version() + ' | Django ' + django.get_version(), flush=True)
print('Database: temporary SQLite memory | external network: blocked', flush=True)
with patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden in A4 tests')):
    failures = Runner(verbosity=2, interactive=False).run_tests(labels)
out = Path(__file__).resolve().parent / 'results'
out.mkdir(exist_ok=True)
summary = {'group': args.group, 'timestamp_utc': datetime.now(timezone.utc).isoformat(),
           'python': platform.python_version(), 'platform': platform.platform(),
           'packages': {n: importlib.metadata.version(n) for n in ['Django','cryptography','requests','whitenoise']},
           'count': len(records), 'failures': failures, 'tests': records}
(out / (args.group + '.json')).write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(f'RESULT: {len(records)} tests | {sum(r["status"] == "PASS" for r in records)} PASS | {failures} failures/errors', flush=True)
print('Evidence: results/' + args.group + '.json', flush=True)
sys.exit(bool(failures))
