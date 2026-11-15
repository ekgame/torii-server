"""Add the tables and columns the models have but no migration creates.

Only for a fresh test database: an existing deployment got these by hand, so its
migrations never needed them. Run after the migrations, before the server starts.
"""

import asyncio

from app.dependencies.database import engine

import main  # noqa: F401  (imports every model)
from sqlalchemy import inspect, text
from sqlalchemy.schema import CreateColumn
from sqlmodel import SQLModel


def fill(conn) -> None:
    existing = set(inspect(conn).get_table_names())
    missing_tables = [t for t in SQLModel.metadata.sorted_tables if t.name not in existing]
    SQLModel.metadata.create_all(conn, tables=missing_tables)
    for table in missing_tables:
        print(f"created table {table.name}")

    for table in SQLModel.metadata.sorted_tables:
        if table.name not in existing:
            continue
        columns = {c["name"] for c in inspect(conn).get_columns(table.name)}
        for column in table.columns:
            if column.name in columns:
                continue
            definition = CreateColumn(column).compile(dialect=conn.dialect)
            conn.execute(text(f"ALTER TABLE `{table.name}` ADD COLUMN {definition}"))
            if column.index:
                conn.execute(text(f"CREATE INDEX `ix_{table.name}_{column.name}` ON `{table.name}` (`{column.name}`)"))
            print(f"added column {table.name}.{column.name}")


async def run() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(fill)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
