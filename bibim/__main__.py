from __future__ import annotations

import argparse
import os
import json
import re

import requests
import feedparser
from scholarly import scholarly
import openai

from .search import search_reference
from .index import Index, IndexTemplate
from .page import Page, PageTemplate

BIBIM_DIR = ".bibim"
CONFIG_FILE = f"{BIBIM_DIR}/settings.json"


class Config:
    path: str
    entries: dict

    def __init__(self, path: str, entries: dict):
        self.path = path
        self.entries = entries

    @staticmethod
    def create(path: str = CONFIG_FILE) -> Config:
        with open(path, 'w') as f:
            settings = {
                "index": {
                    "path": "index.md",
                    "separator": ["# ", "\n"],
                    "headers": {
                        "title": "Title",
                        "authors_concise": "Authors",
                        "venue": "Venus",
                        "year": "Year",
                        "num_citations": "Citations",
                        "reference": "Reference"
                    },
                    "columns": ["title", "authors_concise", "venue", "year", "num_citations", "reference"]
                },
                "reference": {
                    "path": "references",
                    "article": {
                        "fields": {
                            "author": ["**Author**: ", "\n"],
                            "title": ["# ", "\n"],
                            "year": ["**Year**: ", "\n"],
                            "url": ["**URL**: ", "\n"],
                            "journal": ["**Journal**: ", "\n"],
                            "volume": ["**Volume**: ", "\n"],
                            "doi": ["**DOI**: ", "\n"],
                            "arxiv": ["**arXiv**: ", "\n"],
                            "abstract": ["**Abstract**: ", "\n"],
                            "num_citations": ["**Citations**: ", "\n"]
                        },
                        "layout": "{title}{author}{journal}{volume}{year}{url}{arxiv}{doi}{num_citations}"
                    },
                    "proceedings": {
                        "fields": {
                            "author": ["**Author**: ", "\n"],
                            "title": ["# ", "\n"],
                            "year": ["**Year**: ", "\n"],
                            "url": ["**URL**: ", "\n"],
                            "booktitle": ["**Venue**: ", "\n"],
                            "publisher": ["**Publisher**: ", "\n"],
                            "doi": ["**DOI**: ", "\n"],
                            "arxiv": ["**arXiv**: ", "\n"],
                            "abstract": ["**Abstract**: ", "\n"],
                            "num_citations": ["**Citations**: ", "\n"]
                        },
                        "layout": "{title}{author}{booktitle}{year}{url}{arxiv}{doi}{num_citations}"
                    },
                    "misc": {
                        "fields": {
                            "author": ["**Author**: ", "\n"],
                            "title": ["# ", "\n"],
                            "year": ["**Year**: ", "\n"],
                            "url": ["**URL**: ", "\n"],
                            "note": ["**Note**: ", "\n"]
                        },
                        "layout": "{title}{author}{year}{url}{note}"
                    },
                },
            }
            json.dump(settings, f, indent=4)

        return Config(path, settings)

    @staticmethod
    def load(path: str = CONFIG_FILE) -> Config:
        """Loads settings from the settings.json file."""
        if not os.path.exists(path):
            print(f"Error: {path} not found. Please run 'bibim init' to initialize.")
            exit(1)

        with open(path, 'r') as f:
            return Config(path, json.load(f))

    @property
    def index_path(self) -> str:
        return self.entries['index']['path']

    @property
    def index_template(self) -> IndexTemplate:
        return IndexTemplate(self.entries['index']['headers'], self.entries['index']['columns'], self.entries['index']['separator'])

    @property
    def reference_path(self) -> str:
        return self.entries['reference']['path']

    @property
    def reference_template(self) -> PageTemplate:
        return PageTemplate(self.entries['reference']['entries'], self.entries['reference']['layout'])


# Initialize bibim repository
def initialize_repository():
    """Initializes a bibim repository by creating index.md and settings.json."""
    os.makedirs(BIBIM_DIR, exist_ok=True)
    cfg = Config.create(CONFIG_FILE)
    Index.create(cfg.index_path, cfg.index_template)
    os.makedirs(cfg.reference_path, exist_ok=True)
    print("Initialized bibim repository.")


def add_reference(title: str, table_name: str | None = None):
    """Adds a reference to the bibliography markdown file."""

    cfg = Config.load(CONFIG_FILE)

    index = Index.load(cfg.index_path, cfg.index_template)

    paper = search_reference(title, ask_user=True)
    if not paper:
        return

    # e.g., gim2023prompt
    paper_id = f"{paper.author[0].last_name.lower()}{paper.year}{paper.title.split()[0].lower()}"
    paper_ref_path = os.path.join(cfg.reference_path, f"{paper_id}.md")

    # increment a, b, c, ... to the filename and see if it exists
    if os.path.exists(paper_ref_path):
        for i in range(ord('a'), ord('z') + 1):
            paper_ref_path = os.path.join(cfg.reference_path, f"{paper_id}{chr(i)}.md")
            if not os.path.exists(paper_ref_path):
                paper_id += f"{chr(i)}"
                break

    index.insert_row(
        {
            "title": paper.title,
            "authors_concise": paper.author_concise,
            "venue": paper.venue,
            "year": paper.year,
            "citations": paper.num_citations,
            "reference": f"[{paper_ref_path}]({paper_ref_path})"
        },
        table_name=table_name)

    Page.create(paper.to_page_entry(), paper_ref_path, cfg.reference_template)

    print(f"Reference '{paper.title}' added as '{paper_id}'.")


def update_references():
    """Updates the references in the bibliography markdown file."""

    cfg = Config.load(CONFIG_FILE)

    index = Index.load(cfg.index_path, cfg.index_template)

    for table_name, table in index.tables.items():

        for i, row in enumerate(table.rows):
            query = f"{row.entry['title']} {row.entry['authors_concise'].split()[-1]}"
            paper = search_reference(query, ask_user=False)

            if not paper:
                print(f"No metadata found for '{row.entry['title']}'. Skipping.")
                continue

            paper_ref_path = row.entry['reference']
            paper_page = Page.load(paper_ref_path, cfg.reference_template)
            paper_page.data = paper.to_page_entry()
            paper_page.save()

            index.update_row(i, {
                "title": paper.title,
                "authors_concise": paper.author_concise,
                "venue": paper.venue,
                "year": paper.year,
                "citations": paper.num_citations,
                "reference": f"[{paper_ref_path}]({paper_ref_path})"
            }, table_name=table_name)


def generate_bibtex(filename):
    cfg = Config.load(CONFIG_FILE)

    index = Index.load(cfg.index_path, cfg.index_template)

    for table_name, table in index.tables.items():

        for row in table.rows:
            page = Page.load(row.entry['reference'], cfg.reference_template)
            paper_id = row.entry['reference'].split('/')[-1].split('.')[0]
            paper = Paper.from_page_entry(page.data)

        ...

    """Generates a bibtex file from the bibliography markdown file."""
    entries, headers = read_table(filename)
    bibtex_entries = ""
    existing_keys = {}
    for entry in entries:
        title_raw = entry.get('Title', '')

        title = title_raw.split('](')[0][1:]
        paper_ref_path = title_raw.split('](')[1][:-1]  # e.g., gim2023prompt

        # read the markdown file
        with open(paper_ref_path, 'r') as f:
            lines = f.readlines()

        # Extract metadata from the markdown file
        authors = ''
        venue = ''
        year = ''
        url_cell = ''
        for line in lines:
            if line.startswith('**Authors**:'):
                authors = line.split(':', 1)[1].strip()
            elif line.startswith('**Venue**:'):
                venue = line.split(':', 1)[1].strip()
            elif line.startswith('**Year**:'):
                year = line.split(':', 1)[1].strip()
            elif line.startswith('**Links**:'):
                url_cell = line.split(':', 1)[1].strip()

        if not (title and authors and year):
            continue
        # Extract the last name of the first author
        first_author_last_name = authors.split(',')[0].split()[-1]
        # Extract the first word of the title
        first_word_title = title.split()[0]
        # Build the base bibtex key
        bibtex_key_base = f"{first_author_last_name}{year}{first_word_title}"
        # Keep only lowercase letters and numbers
        bibtex_key_base = ''.join(c for c in bibtex_key_base.lower() if c.isalnum())
        # Handle duplicates by appending numbers
        bibtex_key = bibtex_key_base
        count = 1
        while bibtex_key in existing_keys:
            count += 1
            bibtex_key = f"{bibtex_key_base}{count}"
        existing_keys[bibtex_key] = True
        # Start building the bibtex entry
        bibtex_entry = f"@article{{{bibtex_key},\n"
        bibtex_entry += f"  title={{{title}}},\n"
        bibtex_entry += f"  author={{{authors}}},\n"
        bibtex_entry += f"  journal={{{venue}}},\n"
        bibtex_entry += f"  year={{ {year} }},\n"
        # Extract URLs from the 'URL' field
        urls = re.findall(r'\[.*?\]\((.*?)\)', url_cell)
        if urls:
            # Add the first URL as the main URL
            bibtex_entry += f"  url={{ {urls[0]} }},\n"
            # If there's an arXiv URL, add it as 'eprint' or as a note
            for url in urls[1:]:
                if 'arxiv.org' in url.lower():
                    bibtex_entry += f"  eprint={{ {url} }},\n"
                else:
                    bibtex_entry += f"  note={{Available at {url}}},\n"
        bibtex_entry += "}\n\n"
        bibtex_entries += bibtex_entry
    bibtex_filename = os.path.splitext(filename)[0] + '.bib'
    with open(bibtex_filename, 'w', encoding='utf-8') as f:
        f.write(bibtex_entries)
    print(f"Bibtex file '{bibtex_filename}' has been generated.")


def main():
    parser = argparse.ArgumentParser(description='Bibim: A command line tool for managing bibliography.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    parser_new = subparsers.add_parser('init', help='Initialize a new bibliography repository')
    parser_add = subparsers.add_parser('add', help='Add a reference')
    parser_add.add_argument('title', help='Paper title')

    parser_update = subparsers.add_parser('update', help='Update the references')
    parser_bibtex = subparsers.add_parser('bibtex', help='Generate a bibtex file')

    args = parser.parse_args()

    if args.command == 'init':
        initialize_repository()
    elif args.command == 'add':
        add_reference(args.title, ask_user=True)
    elif args.command == 'update':
        update_references()
    elif args.command == 'bibtex':
        generate_bibtex()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
