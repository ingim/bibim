from __future__ import annotations

import argparse
import os
import json
import re

import requests
import feedparser
from scholarly import scholarly
import openai

from .reference import ReferencePage, ReferencePageTemplate
from .search import search_reference, replace_bibtex_key
from .index import Index, IndexTemplate

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
                    "page": {
                        "fields": {
                            "author": ["**Author**: ", "\n"],
                            "title": ["# ", "\n"],
                            "year": ["**Year**: ", "\n"],
                            "venue": ["**Venue**: ", "\n"],
                            "url": ["**URL**: ", "\n"],
                        },
                        "layout": "{title}{author}{venue}{year}{url}"
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
    def reference_template(self) -> ReferencePageTemplate:
        return ReferencePageTemplate(self.entries['reference']['page']['entries'], self.entries['reference']['page']['layout'])


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

    ref = search_reference(title, ask_user=True)
    if not ref:
        return

    # e.g., gim2023prompt
    ref_id = f"{ref.author_last_names[0].lower()}{ref.year}{ref.title.split()[0].lower()}"
    ref_page_path = os.path.join(cfg.reference_path, f"{ref_id}.md")

    # increment a, b, c, ... to the filename and see if it exists
    if os.path.exists(ref_page_path):
        for i in range(ord('a'), ord('z') + 1):
            ref_page_path = os.path.join(cfg.reference_path, f"{ref_id}{chr(i)}.md")
            if not os.path.exists(ref_page_path):
                ref_id += f"{chr(i)}"
                break

    # Update the ref id in the reference object
    ref.bibtex = replace_bibtex_key(ref.bibtex, ref_id)
    ref.bibtex_condensed = replace_bibtex_key(ref.bibtex_condensed, ref_id)

    index.insert_row(
        {
            "title": ref.title,
            "authors_concise": ref.author_concise,
            "venue": ref.venue,
            "year": ref.year,
            "citations": ref.num_citations,
            "reference": f"[{ref_page_path}]({ref_page_path})"
        },
        table_name=table_name)

    ReferencePage.create(ref_page_path, ref, cfg.reference_template)

    print(f"Reference '{ref.title}' added as '{ref_id}'.")


def update_references():
    """Updates the references in the bibliography markdown file."""

    cfg = Config.load(CONFIG_FILE)

    index = Index.load(cfg.index_path, cfg.index_template)

    for table_name, table in index.tables.items():

        for i, row in enumerate(table.rows):
            query = f"{row.entry['title']} {row.entry['authors_concise'].split()[-1]}"
            ref = search_reference(query, ask_user=False)

            if not ref:
                print(f"No metadata found for '{row.entry['title']}'. Skipping.")
                continue

            ref_path = row.entry['reference']
            ref_page = ReferencePage.load(ref_path, cfg.reference_template)
            ref_page.update(ref)

            index.update_row(i, {
                "title": ref.title,
                "authors_concise": ref.author_concise,
                "venue": ref.venue,
                "year": ref.year,
                "citations": ref.num_citations,
                "reference": f"[{ref_path}]({ref_path})"
            }, table_name=table_name)


def generate_bibtex(path: str = 'references', condensed: bool = True):
    cfg = Config.load(CONFIG_FILE)

    index = Index.load(cfg.index_path, cfg.index_template)

    lines = []

    for table_name, table in index.tables.items():

        lines.append("%" * 40)
        lines.append(f"% {table_name}")
        lines.append("%" * 40)

        for row in table.rows:
            page = ReferencePage.load(row.entry['reference'], cfg.reference_template)

            if condensed:
                if page.ref.bibtex_condensed is None:
                    lines.append(page.ref.bibtex)
                else:
                    lines.append(page.ref.bibtex_condensed)
            else:
                lines.append(page.ref.bibtex)

    path = path + '.bib'
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"Bibtex file '{path}.bib' has been generated.")


def main():
    parser = argparse.ArgumentParser(description='Bibim: A command line tool for managing bibliography.')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    parser_new = subparsers.add_parser('init', help='Initialize a new bibliography repository')
    parser_add = subparsers.add_parser('add', help='Add a reference')
    parser_add.add_argument('title', help='Paper title')
    parser_add.add_argument('--table', help='Table name', default=None)

    parser_update = subparsers.add_parser('update', help='Update the references')
    parser_bibtex = subparsers.add_parser('bibtex', help='Generate a bibtex file')
    parser_bibtex.add_argument('--path', help='Bibtex file', default='ref')
    parser_bibtex.add_argument('--condensed', help='Markdown file', default=True)

    args = parser.parse_args()

    if args.command == 'init':
        initialize_repository()
    elif args.command == 'add':
        add_reference(args.title, args.table)
    elif args.command == 'update':
        update_references()
    elif args.command == 'bibtex':
        generate_bibtex(args.path, args.condensed)
    else:
        parser.print_help()

    if __name__ == '__main__':
        main()
