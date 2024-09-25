from __future__ import annotations

import re


def extract_between(text: str, prefix: str, suffix: str):
    pattern = re.escape(prefix) + r'(.+?)' + re.escape(suffix)
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None


class Template:
    headers: dict[str, str]
    columns: list[str]
    separator: (str, str)

    def __init__(self, headers: dict[str, str], columns: list[str], separator: (str, str)):
        self.headers = headers
        self.columns = columns
        self.separator = separator


class Index:
    tables: dict[str, Table]
    template: Template

    def __init__(self):
        self.tables = {}

    def load(self, path: str, template: Template):

        # Load tables from path
        with open(path, 'r') as f:
            lines = f.readlines()

        # Find the start of the table
        table_start = None

        _table_signature = re.sub(r'\s+', '', '|'.join(template.columns))
        table_title = None

        i = 0

        while i < len(lines):
            line = lines[i]
            _table_title = extract_between(line, template.separator[0], template.separator[1])
            if _table_title:
                table_title = _table_title

            # remove all whitespace in line using regex
            if _table_signature == re.sub(r'\s+', '', line):
                ...
            table_start = i + 1 # skip the header line

            # find the end of the table
            while i < len(lines):
                if not line.strip().startswith('|'):
                    break
                i += 1



        if table_start is None:
            print(f"No table found in '{path}'.")
            return [], []

        # Extract the table lines
        table_lines = lines[table_start:]
        # Remove all separator lines
        table_lines = [line for line in table_lines if not re.match(r'^\|\s*(-+\s*\|)+\s*$', line.strip())]

        # Parse the table
        headers_line = table_lines[0]
        headers = [h.strip() for h in headers_line.strip().strip('|').split('|')]
        entries = []
        for line in table_lines[2:]:
            if not line.strip().startswith('|'):
                break  # End of table
            values = [v.strip() for v in line.strip().strip('|').split('|')]
            # Ensure values match headers length
            if len(values) < len(headers):
                values += [''] * (len(headers) - len(values))
            elif len(values) > len(headers):
                values = values[:len(headers)]
            entry = dict(zip(headers, values))

            # parse entry
            title_raw = entry.get('Title', '')
            title = title_raw.split('](')[0][1:]
            paper_ref_path = title_raw.split('](')[1][:-1]  # e.g., ./papers/gim2023prompt.md
            concise_authors = entry.get('Authors', '')
            venue = entry.get('Venue', '')
            year = int(entry.get('Year', '0'))
            num_citations = int(entry.get('Citations', '0'))

            real_entry = PaperIndexItem(
                title=title,
                authors=concise_authors,
                venue=venue,
                year=year,
                num_citations=num_citations,
                paper_ref_path=paper_ref_path
            )

            entries.append(real_entry)

        ...

    def update_row(self, table_name: str, idx: int, values: dict[str, str]):
        ...

    def insert_row(self, table_name: str, values: dict[str, str]):
        ...


class Table:
    parent: Index
    rows: list[Row]

    def __init__(self):
        self.rows = []


class Row:
    parent: Table
    values: dict[str, str]

    def __init__(self):
        ...
