#!/usr/bin/env python3
"""Copy the existing SQLite clinic database into PostgreSQL.

Usage:
    DATABASE_URL='postgresql+psycopg://user:password@host:5432/clinic' \
      python scripts/migrate_sqlite_to_postgres.py

The target schema is created from the application's SQLAlchemy models first.
Existing target rows are not deleted. The script skips rows whose primary key
already exists, making it safe to re-run for an interrupted migration.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    import os
    def load_dotenv(dotenv_path=None, *args, **kwargs):
        if not dotenv_path or not os.path.isfile(dotenv_path):
            return False
        with open(dotenv_path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                if key and key not in os.environ:
                    os.environ[key] = value
        return True
load_dotenv(ROOT / '.env')

from sqlalchemy import create_engine, MetaData, select, insert, text
from sqlalchemy.exc import IntegrityError

from app import create_app
from models import db


def main():
    source = os.environ.get('SQLITE_SOURCE_URL') or f"sqlite:///{ROOT / 'clinic.db'}"
    target = os.environ.get('DATABASE_URL')
    if not target or target.startswith('sqlite'):
        raise SystemExit('Set DATABASE_URL to a PostgreSQL URL before migrating.')

    source_engine = create_engine(source)
    target_app = create_app('production')
    with target_app.app_context():
        target_engine = db.engine
        db.create_all()

        src_meta = MetaData()
        src_meta.reflect(bind=source_engine)
        dst_meta = MetaData()
        dst_meta.reflect(bind=target_engine)

        # Insert parents before children. Repeated passes handle FK ordering
        # without hard-coding every table relationship.
        src_tables = list(src_meta.sorted_tables)
        copied = 0
        skipped = 0
        pending = {t.name for t in src_tables if t.name in dst_meta.tables}

        for _ in range(len(src_tables) + 2):
            progress = False
            for src_table in src_tables:
                if src_table.name not in pending:
                    continue
                dst_table = dst_meta.tables[src_table.name]
                rows = source_engine.connect().execute(select(src_table)).mappings().all()
                if not rows:
                    pending.remove(src_table.name)
                    progress = True
                    continue

                try:
                    with target_engine.begin() as conn:
                        existing_pks = set()
                        pk_cols = list(dst_table.primary_key.columns)
                        if pk_cols:
                            existing_pks = {
                                tuple(row)
                                for row in conn.execute(select(*pk_cols)).all()
                            }
                        for row in rows:
                            if pk_cols:
                                key = tuple(row[c.name] for c in pk_cols)
                                if key in existing_pks:
                                    skipped += 1
                                    continue
                            conn.execute(insert(dst_table).values(dict(row)))
                            copied += 1
                    pending.remove(src_table.name)
                    progress = True
                except IntegrityError:
                    # A parent table may not have been copied yet. Try again
                    # on the next pass.
                    continue

            if not pending or not progress:
                break

        if pending:
            raise SystemExit(f'Migration could not finish; remaining tables: {sorted(pending)}')

        # SQLite preserves explicit integer ids without sequences. PostgreSQL
        # needs each serial/identity sequence moved past the imported rows or
        # the next registration can collide with an existing primary key.
        preparer = target_engine.dialect.identifier_preparer
        with target_engine.begin() as conn:
            for table in dst_meta.sorted_tables:
                pk_cols = list(table.primary_key.columns)
                if len(pk_cols) != 1:
                    continue
                column = pk_cols[0]
                sequence = conn.execute(
                    text('SELECT pg_get_serial_sequence(:table_name, :column_name)'),
                    {'table_name': table.name, 'column_name': column.name},
                ).scalar()
                if not sequence:
                    continue
                quoted_table = preparer.quote(table.name)
                quoted_column = preparer.quote(column.name)
                maximum = conn.execute(
                    text(f'SELECT MAX({quoted_column}) FROM {quoted_table}')
                ).scalar()
                if maximum is None:
                    conn.execute(
                        text('SELECT setval(:sequence_name, 1, false)'),
                        {'sequence_name': sequence},
                    )
                else:
                    conn.execute(
                        text('SELECT setval(:sequence_name, :maximum, true)'),
                        {'sequence_name': sequence, 'maximum': maximum},
                    )

        print(f'Migration complete. Copied: {copied}; skipped existing: {skipped}.')


if __name__ == '__main__':
    main()
