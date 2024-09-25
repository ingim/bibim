import re

import requests





class Author:
    full_name: str
    last_name: str
    concise_name: str

    def __init__(self, full_name: str):
        self.full_name = full_name.strip()
        self.last_name = self.full_name.split()[-1]
        self.concise_name = "".join([n[0].upper() for n in self.full_name.split()[:-1]]) + " " + self.last_name

    def __repr__(self):
        return self.full_name

    def __str__(self):
        return self.full_name


class PaperIndexItem:
    title: str
    authors: str
    venue: str
    year: int
    num_citations: int
    paper_ref_path: str
    paper_id: str

    def __init__(self,
                 title: str,
                 authors: str,
                 venue: str,
                 year: int,
                 num_citations: int,
                 paper_id: str,
                 paper_ref_path: str):
        self.title = title
        self.authors = authors
        self.venue = venue
        self.year = year
        self.num_citations = num_citations
        self.paper_id = paper_id
        self.paper_ref_path = paper_ref_path


class Paper:
    title: str
    authors: list[Author]
    year: int
    venue: str
    url: str
    arxiv_id: str
    abstract: str
    num_citations: int

    def __init__(self,
                 title: str,
                 authors: list[Author],
                 year: int | None = None,
                 venue: str | None = None,
                 url: str | None = None,
                 arxiv_id: str | None = None,
                 abstract: str | None = None,
                 num_citations: int | None = None):

        self.title = title
        self.authors = authors
        self.year = year
        self.venue = venue
        self.url = url
        self.arxiv_id = arxiv_id
        self.abstract = abstract
        self.num_citations = num_citations

    def __eq__(self, other):
        if self.title.lower() != other.title.lower():
            return False

        for a1, a2 in zip(self.authors, other.author):
            if a1.last_name.lower() != a2.last_name.lower():
                return False

        return True

    def get_id(self) -> str:
        first_word_title = self.title.split()[0].lower()
        return f"{self.authors[0].last_name.lower()}{self.year}{first_word_title}"

    def get_url_cell(self) -> str:
        url_cell = ''
        if self.url:
            url_cell += f"[link]({self.url})"
        if self.arxiv_id:
            if url_cell:
                url_cell += ' '
            url_cell += f"[arXiv]({self.arxiv_id})"

        return url_cell

    def get_citation_cell(self) -> str:
        gs_url = f"https://scholar.google.com/scholar?q={requests.utils.quote(self.title)}"
        citation_cell = f"[{self.num_citations}]({gs_url})"
        return citation_cell

    def get_concise_authors(self) -> str:
        concise_authors = [author.concise_name for author in self.authors]
        if len(concise_authors) > 3:
            concise_authors = [concise_authors[0], f'({len(self.authors) - 2})', concise_authors[-1]]

        return ', '.join(concise_authors)


class IndexMarkdown:
    path: str
    lines: list[str]
    headers: list[str]
    entries: list[PaperIndexItem]

    def __init__(self, path: str, lines: list[str], headers: list[str], entries: list[PaperIndexItem]):
        self.path = path
        self.lines = lines
        self.headers = headers
        self.entries = entries

    @staticmethod
    def create_empty(path: str):
        # Create index.md file
        with open(path, 'w') as f:
            f.write("# Bibliography Index\n\n")
            f.write("| Title | Authors | Venue | Year | Citations |\n")
            f.write("|----------|----------|----------|----------|----------|\n")

    @staticmethod
    def open(path: str):
        with open(path, 'r') as f:
            lines = f.readlines()

        # Find the start of the table
        table_start = None
        for i, line in enumerate(lines):
            if line.strip().startswith('|') and 'Title' in line:
                table_start = i
                break

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

        index_markdown = IndexMarkdown(path, lines, headers, entries)
        return index_markdown

    def append(self, entry: PaperIndexItem):
        # for h in self.headers:
        #     if h not in entry:
        #         entry[h] = ''

        self.write(self.entries + [entry])

    def write(self, entries: list[PaperIndexItem]):
        """Writes the list of dictionaries to the markdown file, updating only the table."""
        with open(self.path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the start and end of the table
        lines = content.splitlines()
        table_start = None
        table_end = None

        for i, line in enumerate(lines):
            if line.strip().startswith('|') and 'Title' in line:
                table_start = i
                break

        if table_start is None:
            print(f"No table found in '{self.path}'. Cannot write table.")
            return

        # Find the end of the table
        for j in range(table_start + 1, len(lines)):
            if not lines[j].strip().startswith('|'):
                table_end = j
                break
        else:
            table_end = len(lines)

        # Compute the width of each column based on the max length of the values

        header_sizes = dict(zip(self.headers, [len(h) for h in self.headers]))

        md_entries = []
        for entry in entries:
            md_entry = {
                'Title': entry.title,
                'Authors': entry.authors,
                'Venue': entry.venue,
                'Year': entry.year,
                'Citations': entry.num_citations,
                'Reference': f"[{entry.paper_id}]({entry.paper_ref_path})"
            }
            for h in self.headers:
                if h not in md_entry:
                    md_entry[h] = ''
            md_entries.append(md_entry)

        for entry in md_entries:
            for h in self.headers:
                value = entry.get(h, '')
                header_sizes[h] = max(header_sizes[h], len(value))

        # Build the table content
        table_lines = []
        table_lines.append('| ' + ' | '.join([h.ljust(header_sizes[h]) for h in self.headers]) + ' |')
        table_lines.append('| ' + ' | '.join(['-' * header_sizes[h] for h in self.headers]) + ' |')
        for entry in md_entries:
            row_values = []
            for h in self.headers:
                value = str(entry.get(h, '')).replace('|', '\\|')
                row_values.append(value.ljust(header_sizes[h]))
            row = '| ' + ' | '.join(row_values) + ' |'
            table_lines.append(row)

        # Replace the old table with the new table content
        new_lines = lines[:table_start] + table_lines + lines[table_end:]
        new_content = '\n'.join(new_lines)

        with open(self.path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        self.entries = entries


class PaperMarkdown:
    paper: Paper
    path: str
    lines: list[str]

    def __init__(self, paper: Paper, path: str, lines: list[str]):
        self.paper = paper
        self.path = path
        self.lines = lines

    @staticmethod
    def create(paper: Paper, path: str):
        with open(path, 'w') as f:
            f.write(f"# {paper.title}\n\n")
            f.write(f"**Authors**: {', '.join(str(paper.authors))}\n")
            f.write(f"**Venue**: {paper.venue}\n")
            f.write(f"**Year**: {paper.year}\n")
            f.write(f"**Citations**: {paper.get_citation_cell()}\n")
            f.write(f"**Abstract**: {paper.abstract}\n\n")
            f.write(f"**Links**: {paper.get_url_cell()}\n")

        with open(path, 'r') as f:
            lines = f.readlines()

        return PaperMarkdown(paper, path, lines)

    @staticmethod
    def from_file(path: str):
        with open(path, 'r') as f:
            lines = f.readlines()

            title = lines[0].strip().replace("#", "")
            authors = []
            venue = None
            year = None
            num_citations = None
            url_cell = None

            for line in lines:
                if line.startswith('**Authors**:'):
                    authors = line.split(':', 1)[1].strip()
                elif line.startswith('**Venue**:'):
                    venue = line.split(':', 1)[1].strip()
                elif line.startswith('**Year**:'):
                    year = int(line.split(':', 1)[1].strip())
                elif line.startswith('**Links**:'):
                    url_cell = line.split(':', 1)[1].strip()
                elif line.startswith('**Citations**:'):
                    num_citations = line.split(':', 1)[1].strip()

            # parse url cell
            if url_cell:
                url_cell = url_cell.split()
                url = None
                arxiv_id = None
                for cell in url_cell:
                    if cell.startswith("[link]("):
                        url = cell.split("(", 1)[1].split(")")[0]
                    elif cell.startswith("[arXiv]("):
                        arxiv_id = cell.split("(", 1)[1].split(")")[0]

            # parse citations
            if num_citations:
                num_citations = int(num_citations.split("]")[0][1:])

            # parse authors
            authors = [Author(a.strip()) for a in authors.split(',')]

            # paper
            paper = Paper(
                title=title,
                authors=authors,
                year=year,
                venue=venue,
                url=url,
                arxiv_id=arxiv_id,
                num_citations=num_citations
            )
            return PaperMarkdown(paper, path, lines)

    def update(self, paper: Paper):

        # compare the old and new papers
        if self.paper == paper:
            return

        replacements = {
            'Authors': ', '.join(str(paper.authors)),
            'Venue': paper.venue,
            'Year': paper.year,
            'Citations': paper.get_citation_cell(),
            'Abstract': paper.abstract,
            'Links': paper.get_url_cell()
        }

        # update the paper
        # Precompile regular expressions for each key in the replacements dictionary
        patterns = {key: re.compile(rf'^\*\*{key}\*\*:.*') for key in replacements}

        # Read the file contents
        with open(self.path, 'r') as file:
            lines = file.readlines()

        # Create a new list for modified lines
        modified_lines = []

        # Iterate over each line in the file
        for line in lines:
            modified = False
            # Check if the line matches any of the precompiled patterns
            for key, pattern in patterns.items():
                if pattern.match(line):
                    # Replace the line with the new value from the replacements dictionary
                    modified_line = f'**{key}**: {replacements[key]}\n'
                    modified_lines.append(modified_line)
                    modified = True
                    break  # Move to the next line after modifying
            if not modified:
                # If the line wasn't modified, keep it unchanged
                modified_lines.append(line)

        # Write the modified lines back to the file
        with open(self.path, 'w') as file:
            file.writelines(modified_lines)
