from __future__ import annotations

import re


def extract_between(text: str, prefix: str, suffix: str) -> str | None:
    pattern = re.escape(prefix) + r'(.+?)' + re.escape(suffix)
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None


def strip_markdown_link(text: str) -> str:
    pattern = r'\[([^\]]+)\]\([^\)]+\)'
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return text


class Template:
    headers: dict[str, str]
    columns: list[str]
    separator: (str, str)

    def __init__(self, headers: dict[str, str], columns: list[str], separator: (str, str)):
        self.headers = headers
        self.columns = columns
        self.separator = separator


class Index:
    path: str
    tables: dict[str, Table]
    template: Template

    def __init__(self, path: str, template: Template):
        self.path = path
        self.template = template
        self.tables = {}

    @staticmethod
    def load(path: str, template: Template) -> Index:

        index = Index(path, template)

        # Load tables from path
        with open(path, 'r') as f:
            lines = f.readlines()

        # Find the start of the table
        _table_signature = re.sub(r'\s+', '', '|'.join(template.columns))
        table_title = None

        i = 0

        while i < len(lines):
            line = lines[i]
            _table_title = extract_between(line, template.separator[0], template.separator[1])
            if _table_title:
                table_title = _table_title

            # remove all whitespace in line using regex
            if _table_signature != re.sub(r'\s+', '', line):
                i += 1
                continue

            table_start = i + 2  # skip the header line and the separator line

            # find the end of the table
            while i < len(lines):
                if not line.strip().startswith('|'):
                    break
                i += 1

            table_end = i

            if table_end <= table_start:
                # empty table
                index.tables[table_title] = Table(table_start, table_start)
                continue

            table_lines = lines[table_start:table_end]

            # parse table lines
            table = Table(table_start, table_end)
            for line in table_lines:
                values = [strip_markdown_link(v.strip()) for v in line.strip().strip('|').split('|')]
                entry = dict(zip(template.columns, values))
                row = Row(table, entry)
                table.rows.append(row)

            index.tables[table_title] = table

        return index

    def update_row(self, table_name: str, idx: int, values: dict[str, str]) -> bool:

        if table_name not in self.tables:
            return False

        table = self.tables[table_name]

        if idx < 0 or idx >= len(table.rows):
            return False

        table.rows[idx].entry = values

        self._write_table(table_name)

        return True

    def insert_row(self, table_name: str, values: dict[str, str]) -> bool:

        if table_name not in self.tables:
            return False

        table = self.tables[table_name]
        row = Row(table, values)
        table.rows.append(row)

        self._write_table(table_name)
        return True

    def _write_table(self, table_name: str):

        table = self.tables[table_name]

        headers = [self.template.headers[c] for c in self.template.columns]
        header_widths = dict(zip(self.template.columns, [len(h) for h in headers]))

        for row in table.rows:
            for c in self.template.columns:
                header_widths[c] = max(header_widths[c], len(row.entry[c]))

        lines = [
            '| ' + ' | '.join([h.ljust(header_widths[h]) for h in headers]) + ' |',
            '| ' + ' | '.join(['-' * header_widths[h] for h in headers]) + ' |'
        ]

        for row in table.rows:
            entry_formatted = [row.entry[c]
                               .replace('|', '\\|')
                               .ljust(header_widths[c])
                               for c in self.template.columns]
            row = '| ' + ' | '.join(entry_formatted) + ' |'
            lines.append(row)

        # Read the file into a list of lines
        with open(self.path, 'r') as file:
            lines_old = file.readlines()

        # Replace lines from n to m (inclusive)
        lines_new = lines_old[:table.start_line - 2] + lines + lines_old[table.end_line + 1:]
        end_line_new = table.start_line + (len(lines) - 2) - 1

        delta = end_line_new - table.end_line

        # Write the updated lines back to the file
        with open(self.path, 'w') as file:
            file.writelines(lines_new)

        table.end_line = end_line_new

        # Update the start and end lines of all tables after the current table
        for table_name in self.tables:
            if self.tables[table_name].start_line > table.start_line:
                self.tables[table_name].start_line += delta
                self.tables[table_name].end_line += delta


class Table:
    rows: list[Row]
    start_line: int
    end_line: int

    def __init__(self, start_line: int, end_line: int):
        self.rows = []
        self.start_line = start_line
        self.end_line = end_line


class Row:
    parent: Table
    entry: dict[str, str]

    def __init__(self, parent: Table, entry: dict[str, str]):
        self.parent = parent
        self.entry = entry
