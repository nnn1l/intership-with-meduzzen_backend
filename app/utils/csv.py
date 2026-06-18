import csv
import io

async def conver_to_csv(data: list[dict]) -> str:
    if not data:
        return ""

    output = io.StringIO()

    fieldnames = data[0].keys()

    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(data)

    return output.getvalue()