import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app.core.database import build_alembic_config, create_db_engine, verify_schema_up_to_date


class PhaseBMigrationTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(prefix="phaseb-migrations-", suffix=".db")
        os.close(fd)
        self.database_url = f"sqlite:///{self.db_path}"

    def tearDown(self):
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_verify_schema_rejects_unmigrated_database(self):
        engine = create_db_engine(self.database_url)
        self.addCleanup(engine.dispose)

        with self.assertRaises(RuntimeError) as ctx:
            verify_schema_up_to_date(engine_instance=engine, database_url=self.database_url)

        self.assertIn("alembic upgrade head", str(ctx.exception))

    def test_alembic_upgrade_creates_schema_and_version(self):
        config = build_alembic_config(self.database_url)
        command.upgrade(config, "head")

        engine = create_db_engine(self.database_url)
        self.addCleanup(engine.dispose)

        verify_schema_up_to_date(engine_instance=engine, database_url=self.database_url)

        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        self.assertIn("users", tables)
        self.assertIn("daily_summaries", tables)
        self.assertIn("alembic_version", tables)
        self.assertIn("alerts", tables)

        alert_columns = {column["name"] for column in inspector.get_columns("alerts")}
        self.assertIn("dedupe_key", alert_columns)

        with engine.connect() as connection:
            version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        expected_head = ScriptDirectory.from_config(config).get_current_head()

        self.assertEqual(version, expected_head)

    def test_cli_alembic_upgrade_honors_database_url_env(self):
        backend_dir = Path(__file__).resolve().parents[1]
        env = os.environ.copy()
        env["DATABASE_URL"] = self.database_url
        env.setdefault("SECRET_KEY", "test-secret-key-change-me-1234567890")

        result = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, msg=result.stderr or result.stdout)

        engine = create_db_engine(self.database_url)
        self.addCleanup(engine.dispose)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        self.assertIn("users", tables)
        self.assertIn("alembic_version", tables)


if __name__ == "__main__":
    unittest.main()
