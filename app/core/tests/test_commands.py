"""
Tests for the wait_for_db management command.
"""
from unittest.mock import patch
from psycopg2 import OperationalError as Psycopg2OpError
from django.core.management import call_command
from django.db.utils import OperationalError
from django.test import TestCase


class CommandTests(TestCase):
    """Tests for wait_for_db management command."""

    @patch('core.management.commands.wait_for_db.Command.check')
    def test_db_ready_immediately(self, patched_check):
        """Test database ready immediately."""
        patched_check.return_value = True
        call_command('wait_for_db')
        patched_check.assert_called_once_with(databases=['default'])

    @patch('time.sleep')
    @patch('core.management.commands.wait_for_db.Command.check')
    def test_wait_for_db_delay(self, patched_check, patched_sleep):
        """Test waiting for database when getting OperationalError."""
        patched_check.side_effect = [Psycopg2OpError] * 2 + \
                                    [OperationalError] * 3 + \
                                    [True]
        call_command('wait_for_db')
        self.assertEqual(patched_check.call_count, 6)
        self.assertEqual(patched_sleep.call_count, 5)

    @patch('time.sleep')
    @patch('core.management.commands.wait_for_db.Command.check')
    def test_db_retries_on_errors(self, patched_check, patched_sleep):
        """Test database retries on both error types."""
        patched_check.side_effect = [
            Psycopg2OpError, OperationalError, True
        ]
        call_command('wait_for_db')
        self.assertEqual(patched_check.call_count, 3)
        self.assertEqual(patched_sleep.call_count, 2)