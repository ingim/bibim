# bibim
[![PyPI version](https://img.shields.io/pypi/v/bibim)](https://pypi.org/project/bibim/)

bibim is a command-line tool designed to simplify bibliography management for computer science research. It allows you to maintain your references directly within markdown files, automatically fetch and update citation data, and generate BibTeX files.


- **Markdown-based bibliography management**: Manage your bibliography within markdown files to seamlessly integrate with your research notes.
- **Automatic BibTeX generation**: Eliminate the hassle of maintaining separate `.bib` files and ensure consistent formatting across your references.
- **Up-to-date references**: Automatically keep your paper attributes current, without manually tracking changes from preprints to published versions.


## Installation

Install bibim using pip:

```bash
pip install bibim
```

## Usage


### 1. Create a new markdown

Initialize a markdown file with a predefined structure for managing your references.
```bash
bibim new ref.md
```

Alternatively, you can add the following table anywhere in an existing markdown file to make it bibim-compatible.
```bash
| Title | Authors | Publication | Year | URL | Citation Count | Summary |
|-------|---------|-------------|------|-----|----------------|---------|
```


### 2. Add a reference

Add a reference to your bibliography markdown file by simply typing the paper title or the author names. The reference will be appended to the table.

```bash
bibim add ref.md "attn is all u need vaswani"
```

- **Automated metadata retrieval**: Searches [Google Scholar](https://scholar.google.com) and [DBLP](https://dblp.org) for the paper title to fill in authors, publication venue, and year.
- **Citation counts**: Retrieves the current citation count from Google Scholar.
- **Paper summary**: Generates a concise summary using OpenAI's API [if an API key is set](https://help.openai.com/en/articles/5112595-best-practices-for-api-key-safety).
- **ArXiv links**: Includes direct links to [arXiv](https://arxiv.org) if the paper is available there.



### 4. Update references

Updates all reference metadata in the bibliography markdown file. This keeps any user-added columns or notes intact.

```bash
bibim update ref.md
```


### 5. Generate a BibTeX file

Generates a BibTeX file from your bibliography markdown file. bibim formats entry IDs as `[author][year][first word of title]` using lowercase letters and numbers.

```bash
bibim bib ref.md
```

## Contributing

We welcome pull requests. For major changes, please open an issue to discuss your ideas before contributing.

## Misc
The first version of bibim was almost entirely written by ChatGPT (o1-preview).

## License

Licensed under the [MIT License](LICENSE).


