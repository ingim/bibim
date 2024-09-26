# bibim

[![PyPI version](https://img.shields.io/pypi/v/bibim)](https://pypi.org/project/bibim/)

`bibim` is a command-line tool that simplifies bibliography management for computer science research. It allows you to
manage references directly within Markdown files, automatically fetch and update citation data, and generate BibTeX
files.

## Features

- **Markdown-based management**: Seamlessly integrate your bibliography within your research notes.
- **Automatic BibTeX generation**: No need to maintain separate `.bib` files; ensures consistent formatting across
  references.
- **Up-to-date references**: Automatically keep paper attributes current without manual tracking from preprints to
  published versions.

## Installation

Requires Python 3.8 or higher.

```bash
$ pip install bibim
```

## Usage

### 1. Initialize a New Repository

Convert a folder into a `bibim` repository:

```bash
$ bibim init
```

This creates an `index.md` file and a `.bibim` directory for preferences.

#### Multiple Tables

You can have multiple tables in `index.md`, each representing a different category (e.g., `System`, `AI`). Add a
Markdown header above each table:

```markdown
# System

# AI
```

#### Customizing Markdown Formatting

Modify formatting options in `.bibim/settings.json`. For example, to change the default column order:

```json
{
  "columns": [
    "title",
    "authors_concise",
    "venue",
    "year",
    "num_citations",
    "reference"
  ]
}
```

### 2. Add a Reference

Add a reference by providing the paper title or author names:

```bash
$ bibim add "attention is all you need vaswani"
```

This creates a new file in `./references/{author}{year}{firstwordoftitle}.md` with full metadata and updates `index.md`
with concise metadata (abbreviated author names, title, venue, year, citation count, and a link to the full reference).

- **Automated metadata retrieval**: Searches [Google Scholar](https://scholar.google.com) and [DBLP](https://dblp.org)to
  fill in authors, venue, and year.
- **Citation counts**: Retrieves current citation counts from Google Scholar.
- **arXiv links**: Includes direct links if available.

#### Specify a Target Table

Add a reference to a specific table:

```bash
$ bibim add "few shot learners" --table "ai"
```

Table titles are case-insensitive. If not specified, the reference is added to the first table in `index.md`.

### 3. Update References

Update all reference metadata, keeping any user-added columns or notes intact:

```bash
$ bibim update
```

You can also update a specific table:

```bash
$ bibim update --table "ai"
```

### 4. Generate a BibTeX File

Generate a BibTeX file from your bibliography:

```bash
$ bibim bibtex
```

Entry IDs are formatted as `[author][year][firstwordoftitle]` in lowercase.

### 5. Formatting Markdown

To beautify the `index.md`, run:

```bash
$ bibim format
```

## Contributing

We welcome pull requests. For major changes, please open an issue to discuss your ideas.

## License

[MIT License](LICENSE)
