from __future__ import annotations

import re


def find_best_matching_table(table_titles: list[str], query: str) -> str | None:
    # Preprocess the query
    query_lower = query.lower()
    query_words = set(re.findall(r'\w+', query_lower))

    # Check for exact matches (case-insensitive)
    for title in table_titles:
        if title.lower() == query_lower:
            return title

    # Check for substring matches (case-insensitive)
    for title in table_titles:
        if query_lower in title.lower():
            return title
        if title.lower() in query_lower:
            return title

    # Compute Jaccard similarity between the query and each paper title
    max_similarity = 0
    best_match = None

    for title in table_titles:
        title_lower = title.lower()
        title_words = set(re.findall(r'\w+', title_lower))

        # Calculate Jaccard similarity
        intersection = query_words & title_words
        union = query_words | title_words
        if not union:
            continue
        similarity = len(intersection) / len(union)

        # Update the best match if the similarity is higher
        if similarity > max_similarity:
            max_similarity = similarity
            best_match = title

    # Return the best match if similarity is above a threshold
    threshold = 0.5
    if max_similarity >= threshold:
        return best_match
    else:
        return None


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


class IndexTemplate:
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
    template: IndexTemplate

    def __init__(self, path: str, template: IndexTemplate):
        self.path = path
        self.template = template
        self.tables = {}

    @staticmethod
    def create(path: str, template: IndexTemplate) -> Index:

        headers = [template.headers[c] for c in template.columns]
        header_widths = dict(zip(template.columns, [len(h) for h in headers]))

        lines = [
            template.separator[0] + 'Index' + template.separator[1] + '\n',
            '| ' + ' | '.join(headers) + ' |\n',
            '|' + '|'.join(['-' * (header_widths[c] + 2) for c in template.columns]) + '|\n'
        ]

        with open(path, 'w') as f:
            f.write(''.join(lines))

        return Index.load(path, template)

    @staticmethod
    def load(path: str, template: IndexTemplate) -> Index:
        index = Index(path, template)

        # Load tables from path
        with open(path, 'r') as f:
            lines = f.readlines()

        # Find the start of the table
        _headers = [template.headers[c] for c in template.columns]
        _table_signature = re.sub(r'\s+', '', '|' + '|'.join(_headers) + '|')
        table_title = None

        i = 0
        while i < len(lines):
            line = lines[i]
            _table_title = extract_between(line, template.separator[0], template.separator[1])

            if _table_title:
                table_title = _table_title

            # remove all whitespace in line using regex
            i += 1
            if _table_signature != re.sub(r'\s+', '', line):
                continue
            # print('found table', table_title)
            table_start = i + 1  # skip the header line and the separator line
            # print('table start', table_start)

            # find the end of the table
            while i < len(lines):
                if not lines[i].strip().startswith('|'):
                    break
                i += 1

            table_end = i
            # print('table end', table_end)

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

    def update_row(self, idx: int, values: dict[str, str], table_name: str | None = None) -> bool:

        if not table_name:
            table_name = list(self.tables.keys())[0]
        else:
            table_name = find_best_matching_table(list(self.tables.keys()), table_name)

        if table_name is None:
            return False

        table = self.tables[table_name]

        if idx < 0 or idx >= len(table.rows):
            return False

        table.rows[idx].entry = values

        self._write_table(table_name)

        return True

    def insert_row(self, values: dict[str, str], table_name: str | None = None) -> bool:

        if not table_name:
            table_name = list(self.tables.keys())[0]
        else:
            table_name = find_best_matching_table(list(self.tables.keys()), table_name)

        if table_name is None:
            return False

        table = self.tables[table_name]

        row = Row(table, values)
        table.rows.append(row)

        self._write_table(table_name)
        return True

    def format(self):
        for table_name in self.tables:
            self._write_table(table_name)

    def _write_table(self, table_name: str):

        table = self.tables[table_name]

        headers = [self.template.headers[c] for c in self.template.columns]
        header_widths = dict(zip(self.template.columns, [len(h) for h in headers]))

        for row in table.rows:

            # linkify reference
            if 'reference' in row.entry:
                row.entry['reference'] = f"[{row.entry["reference"]}]({row.entry['reference']})"

            for c in self.template.columns:
                header_widths[c] = max(header_widths[c], len(row.entry[c]))

        lines = [
            '| ' + ' | '.join([self.template.headers[c].ljust(header_widths[c]) for c in self.template.columns]) + ' |\n',
            '|' + '|'.join(['-' * (header_widths[c] + 2) for c in self.template.columns]) + '|\n'
        ]

        for row in table.rows:
            entry_formatted = [row.entry[c]
                               .replace('|', '\\|')
                               .ljust(header_widths[c])
                               for c in self.template.columns]
            row = '| ' + ' | '.join(entry_formatted) + ' |\n'
            lines.append(row)

        # Read the file into a list of lines
        with open(self.path, 'r') as file:
            lines_old = file.readlines()

        # Replace lines from n to m (inclusive)
        lines_new = lines_old[:table.start_line - 2] + lines + lines_old[table.end_line:]
        end_line_new = table.start_line + len(table.rows)

        delta = end_line_new - table.end_line

        # Write the updated lines back to the file
        with open(self.path, 'w') as file:
            file.write(''.join(lines_new))

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
