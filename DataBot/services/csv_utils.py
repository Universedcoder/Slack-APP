import csv
import io

from DataBot.services.db import QueryResult


def generate_csv(result: QueryResult) -> str:
    """Serialize a QueryResult to a CSV string (header + rows)."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=result.columns, lineterminator="\r\n")
    writer.writeheader()
    writer.writerows(result.rows)
    return output.getvalue()
