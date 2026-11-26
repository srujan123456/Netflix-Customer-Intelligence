
from sqlglot import parse, exp


FORBIDDEN_NODES = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Alter,
    exp.TruncateTable,
    exp.Command,
)


def validate_sql(sql, schema, max_rows=500):

    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("SQL query cannot be empty.")

    if not isinstance(schema, dict) or not schema:
        raise ValueError("A valid database schema is required.")

    if not isinstance(max_rows, int) or isinstance(max_rows, bool) or max_rows < 1:
        raise ValueError("max_rows must be a positive integer.")

    statements = parse(sql, read="postgres")

    if len(statements) != 1 or statements[0] is None:
        raise ValueError("Only one SQL statement is allowed.")

    query = statements[0]

    if not isinstance(query, exp.Select):
        raise ValueError("Only SELECT queries are permitted.")

    for node_type in FORBIDDEN_NODES:
        if any(query.find_all(node_type)):
            raise ValueError("Forbidden SQL operation detected.")

    if query.find(exp.Into) or query.find(exp.Lock):
        raise ValueError("SELECT INTO and locking queries are not permitted.")

    if query.find(exp.CTE) or query.find(exp.Subquery):
        raise ValueError("CTEs and subqueries are not supported yet.")

    allowed_schema = {
        table.lower(): {column.lower() for column in columns}
        for table, columns in schema.items()
    }

    table_aliases = {}
    referenced_tables = set()

    for table in query.find_all(exp.Table):

        table_name = table.name.lower()
        schema_name = table.db.lower() if table.db else None

        if schema_name is not None and schema_name != "public":
            raise ValueError("Only the public schema is permitted.")

        if table.catalog:
            raise ValueError("Database-qualified tables are not permitted.")

        if table_name not in allowed_schema:
            raise ValueError(f"Unknown table: {table_name}")

        referenced_tables.add(table_name)

        alias = table.alias_or_name.lower()
        table_aliases[alias] = table_name
        table_aliases[table_name] = table_name

    if not referenced_tables:
        raise ValueError("Query must reference an allowed table.")

    output_aliases = {
        projection.alias.lower()
        for projection in query.expressions
        if projection.alias
    }

    for column in query.find_all(exp.Column):

        column_name = column.name.lower()

        if column_name == "*":
            if column.table and column.table.lower() not in table_aliases:
                raise ValueError(f"Unknown table alias: {column.table}")
            continue

        if column_name in output_aliases and not column.table:
            continue

        if column.table:

            qualifier = column.table.lower()

            if qualifier not in table_aliases:
                raise ValueError(f"Unknown table alias: {qualifier}")

            actual_table = table_aliases[qualifier]

            if column_name not in allowed_schema[actual_table]:
                raise ValueError(
                    f"Unknown column '{column_name}' in table '{actual_table}'."
                )

        else:

            matching_tables = [
                table
                for table in referenced_tables
                if column_name in allowed_schema[table]
            ]

            if not matching_tables:
                raise ValueError(f"Unknown column: {column_name}")

            if len(matching_tables) > 1:
                raise ValueError(
                    f"Ambiguous column: {column_name}. "
                    "Qualify it with a table name."
                )

    limit = query.args.get("limit")

    if limit is None:
        query = query.limit(max_rows)

    else:
        limit_value = limit.expression

        if not isinstance(limit_value, exp.Literal) or not limit_value.is_int:
            raise ValueError("LIMIT must be a positive integer.")

        if int(limit_value.this) < 1:
            raise ValueError("LIMIT must be a positive integer.")

        if int(limit_value.this) > max_rows:
            query = query.limit(max_rows)

    return query.sql(dialect="postgres")
