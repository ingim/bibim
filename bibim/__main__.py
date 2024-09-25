import argparse
import os
import json
import re

import requests
import feedparser
from scholarly import scholarly
import openai

from .paper import Paper, Author, PaperMarkdown, IndexMarkdown

SETTINGS_FILE = ".bibim/settings.json"


# Initialize bibim repository
def init_repository():
    """Initializes a bibim repository by creating index.md and settings.json."""
    os.makedirs(".bibim", exist_ok=True)
    with open(SETTINGS_FILE, 'w') as f:
        settings = {
            "index": "index.md",
            "references": "./references",
            "paper_template": {
                "entries": {
                    "title": ["# ", "\n"],
                    "authors": ["**Authors**: ", "\n"],
                    "venue": ["**Venue**: ", "\n"],
                    "year": ["**Year**: ", "\n"],
                    "abstract": ["**Abstract**: ", "\n"],
                    "links": ["**Links**: ", "\n"],
                },
                "layout": "{title}{authors}{venue}{year}{abstract}{links}"
            },
            "index_template": {
                "separator": ["# ", "\n"],
                "headers": {
                    "title": "Title",
                    "concise_authors": "Authors",
                    "venue": "Venus",
                    "year": "Year",
                    "citations": "Citations",
                    "reference": "Reference"
                },
                "columns": ["title", "concise_authors", "venue", "year", "citations", "reference"]
            }

        }
        json.dump(settings, f, indent=4)

    # Create index.md file
    IndexMarkdown.create_empty('index.md')

    os.makedirs("./references", exist_ok=True)

    print("Initialized bibim repository.")


# Read the settings file
def load_settings():
    """Loads settings from the settings.json file."""
    if not os.path.exists(SETTINGS_FILE):
        print(f"Error: {SETTINGS_FILE} not found. Please run 'bibim init' to initialize.")
        exit(1)

    with open(SETTINGS_FILE, 'r') as f:
        return json.load(f)


def search_arxiv(title: str, authors: list[Author] | None = None) -> Paper | None:
    """Searches arXiv for the paper title and authors' last names, returns the arXiv URL if found."""
    query = f"ti:\"{title}\""
    if authors:
        # Include the first authors' last name to improve search accuracy
        query += '+AND+au:\"' + authors[0].last_name + '\"'
    # Construct the search query
    url = f"https://export.arxiv.org/api/query?search_query={requests.utils.quote(query)}&max_results=1"
    response = requests.get(url)
    if response.status_code != 200:
        print("Error accessing arXiv API.")
        return
    feed = feedparser.parse(response.content)
    if feed.entries:
        entry = feed.entries[0]
        arxiv_id = entry.get('id', '')

        # Ensure that the title matches
        arxiv_title = re.sub(r"\s+", " ", entry.get('title', '')).strip()
        if title.lower() != arxiv_title.lower():
            return

        return Paper(
            title=arxiv_title,
            authors=authors,
            arxiv_id=arxiv_id,
        )
    else:
        return


def search_google_scholar(title: str, max_results: int = 3) -> list[Paper]:
    """Searches for the paper title on Google Scholar and returns matching papers."""
    search_query = scholarly.search_pubs(title)
    papers = []
    try:
        for _ in range(max_results):
            paper = next(search_query)

            paper_title = paper['bib'].get('title', '').strip()
            paper_authors_data = paper['bib'].get('author', '').strip()
            if isinstance(paper_authors_data, str):
                paper_authors = [Author(author) for author in re.split(' and ', paper_authors_data)]
            elif isinstance(paper_authors_data, list):
                paper_authors = [Author(author) for author in paper_authors_data]
            else:
                paper_authors = []

            paper_num_citations = paper.get('num_citations', 0)
            paper_abstract = paper['bib'].get('abstract', '')
            paper_url = paper.get('pub_url', '')

            paper = Paper(
                title=paper_title,
                authors=paper_authors,
                url=paper_url,
                abstract=paper_abstract,
                num_citations=paper_num_citations
            )

            papers.append(paper)
    except StopIteration:
        pass

    return papers


def search_dblp(title: str, authors: list[Author] | None = None) -> Paper | None:
    """Searches for the paper on DBLP using title and authors."""
    query = title
    if authors:
        # Include authors' last names in the query to improve accuracy
        authors_last_name = [author.last_name for author in authors]
        query += ' ' + ' '.join(authors_last_name)

    url = f'https://dblp.org/search/publ/api?q={requests.utils.quote(query)}&format=json'
    response = requests.get(url)
    data = response.json()
    hits = data.get('result', {}).get('hits', {}).get('hit', [])

    def parse_entry(entry: dict) -> Paper:

        info = entry.get('info', {})
        paper_title_raw = info.get('title')
        paper_authors_raw = info.get('authors', {}).get('author', [])

        # parse title
        paper_title = re.sub(r'\s+', ' ', paper_title_raw).strip()

        if paper_title.endswith('.'):
            paper_title = paper_title[:-1]

        # parse authors
        if not isinstance(paper_authors_raw, list):
            paper_authors_raw = [paper_authors_raw]

        paper_authors = []
        for author in paper_authors_raw:
            author_name = author.get('text', '') if isinstance(author, dict) else author
            author_name_clean = re.sub(r'\s+\d{4}$', '', author_name)
            paper_authors.append(Author(author_name_clean))

        # parse venue
        paper_venue = info.get('venue')

        # parse year
        paper_year = int(info.get('year'))

        # parse URL
        paper_url = info.get('ee')

        return Paper(
            title=paper_title,
            authors=paper_authors,
            venue=paper_venue,
            year=paper_year,
            url=paper_url
        )

    if hits:
        # Attempt to find an exact match
        for entry in hits:
            paper = parse_entry(entry)
            if paper.title.lower() == title.lower():
                if authors and len(authors) > 1:
                    if paper.authors[0].last_name.lower() != authors[0].last_name.lower():
                        continue
                return paper

    print(f"No results found for '{title}' on DBLP.")
    return None


def generate_summary(abstract):
    """Generates a concise summary using OpenAI API."""
    if openai is None:
        print("OpenAI API is not available.")
        return "Summary not available."
    try:
        openai.api_key = os.getenv('OPENAI_API_KEY')
        if not openai.api_key:
            print("OpenAI API key is not set in the environment variables.")
            return "Summary not available."

        client = openai.OpenAI()

        stream = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user",
                       "content": f"Summarize the following paper abstract in a clear and concise manner, highlighting the core ideas, key findings, and major results. Ensure the summary captures the problem the research addresses, the methods used, and the most important outcomes or conclusions drawn from the study.:\n\n{abstract}"}],
            stream=True,
        )

        summary = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                summary += chunk.choices[0].delta.content
        return summary.strip()
    except Exception as e:
        print(f"Error generating summary: {e}")
        return "Summary not available."


def find_paper(title: str, ask_user: bool = False) -> Paper | None:
    # Step 1. Search on Google Scholar
    print(f"Searching on Google Scholar...")
    papers = search_google_scholar(title)
    if not papers:
        print(f"No results found on Google Scholar.")
        return
    elif len(papers) == 1:
        google_paper = papers[0]
    elif ask_user:
        # Prompt the user to choose one
        print(f"Multiple papers found on Google Scholar:")
        for idx, paper in enumerate(papers):
            paper_authors_str = paper.authors[0].full_name + (' et al.' if len(paper.authors) > 1 else '')
            print(f"    {idx + 1}. {paper.title} by {paper_authors_str}")
        try:
            choice = int(input(f"Please select the correct paper (1-{len(papers)}) or 0 to cancel: "))
            if choice == 0:
                return
            elif 1 <= choice <= len(papers):
                google_paper = papers[choice - 1]
            else:
                return
        except ValueError:
            return
    else:
        google_paper = papers[0]

    # Step 3. Search on DBLP using the title and authors
    print(f"Searching on DBLP...")
    dblp_paper = search_dblp(google_paper.title, google_paper.authors)

    if not dblp_paper:
        print(f"No results found on DBLP.")
        return

    # Step 4. Search on arXiv using the title and authors
    print(f"Searching on arXiv...")
    arxiv_paper = search_arxiv(google_paper.title, google_paper.authors)

    # Step 5. Consolidate the metadata
    paper = Paper(
        title=dblp_paper.title,
        authors=dblp_paper.authors,
        year=dblp_paper.year,
        venue=dblp_paper.venue,
        url=dblp_paper.url,
        arxiv_id=arxiv_paper.arxiv_id if arxiv_paper else None,
        abstract=google_paper.abstract,
        num_citations=google_paper.num_citations
    )

    return paper


def add_reference(title):
    """Adds a reference to the bibliography markdown file."""

    settings = load_settings()
    index_file = settings.get("index", "index.md")
    references_dir = settings.get("references", "./references")

    index_md = IndexMarkdown.open(index_file)
    paper = find_paper(title, ask_user=True)

    if not paper:
        return

    # get paper id
    paper_id = paper.get_id()  # e.g., gim2023prompt
    paper_ref_path = os.path.join(references_dir, paper_id + ".md")

    if os.path.exists(paper_ref_path):
        # increment a, b, c, ... to the filename and see if it exists
        for i in range(97, 123):
            paper_ref_path = os.path.join(references_dir, paper_id + f"{chr(i)}.md")
            if not os.path.exists(paper_ref_path):
                paper_id += f"{chr(i)}"
                break

    PaperMarkdown.create(paper, paper_ref_path)

    # Prepare the reference entry as a dictionary
    entry = {
        'Title': f'[{paper.title}]({paper_ref_path})',
        'Authors': paper.get_concise_authors(),
        'Venue': paper.venue,
        'Year': paper.year,
        'Citations': paper.num_citations,
    }

    index_md.append(entry)

    print(f"Reference '{paper.title}' added as '{paper_id}'.")


def update_references():
    """Updates the references in the bibliography markdown file."""

    settings = load_settings()
    index_file = settings.get("index", "index.md")

    # Read the index file
    index_md = IndexMarkdown.open(index_file)

    new_entries = []

    # Update each reference
    for entry in index_md.entries:
        title_raw = entry.get('Title', '')
        title = title_raw.split('](')[0][1:]
        paper_ref_path = title_raw.split('](')[1][:-1]  # e.g., gim2023prompt

        print(f"Updating '{title}'...")

        paper = find_paper(title + " " + entry.get('Authors', '').split()[-1], ask_user=False)

        if not paper:
            print(f"No metadata found for '{title}'. Skipping.")
            new_entries.append(entry)
            continue

        # read markdown
        existing_paper_file = PaperMarkdown.from_file(paper_ref_path)
        existing_paper_file.update(paper)

        # Prepare the reference entry as a dictionary
        new_entry = {
            'Title': f'[{paper.title}]({paper_ref_path})',
            'Authors': paper.get_concise_authors(),
            'Venue': paper.venue,
            'Year': paper.year,
            'Citations': paper.num_citations,
        }

        # Ensure all headers are present in the entry
        for h in headers:
            if h not in new_entry:
                new_entry[h] = ''

        new_entries.append(new_entry)
        print(f"Updated '{title}'.")

    # Write back the table
    write_table(index_file, new_entries, headers)
    print(f"References have been updated.")


def generate_bibtex(filename):
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
        init_repository()
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
