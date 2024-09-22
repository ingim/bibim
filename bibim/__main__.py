import argparse
import os
import re
import requests
import feedparser
from scholarly import scholarly
import openai


def create_new_bibliography(filename):
    """Creates a new markdown file with the necessary table headers."""
    with open(filename, 'w') as f:
        f.write("# Bibliography\n\n")
        f.write("| Title | Authors | Publication | Year | URL | Citation Count | Summary |\n")
        f.write("|-------|---------|-------------|------|-----|----------------|---------|\n")
    print(f"New bibliography file '{filename}' created.")


def search_arxiv(title, authors=None):
    """Searches arXiv for the paper title and authors' last names, returns the arXiv URL if found."""
    query = f"ti:\"{title}\""
    if authors:
        # Extract authors' last names
        authors_last_name = [author.split()[-1] for author in authors]
        # Include authors' last names in the query to improve accuracy
        query += ' '.join(authors_last_name)
    # Construct the search query
    url = f"https://export.arxiv.org/api/query?search_query={requests.utils.quote(query)}&max_results=1"
    response = requests.get(url)
    if response.status_code != 200:
        print("Error accessing arXiv API.")
        return None
    feed = feedparser.parse(response.content)
    if feed.entries:
        entry = feed.entries[0]
        arxiv_url = entry.get('id', '')
        return arxiv_url
    else:
        return None


def search_google_scholar(title):
    """Searches for the paper title on Google Scholar and returns matching papers."""
    search_query = scholarly.search_pubs(title)
    papers = []
    try:
        for _ in range(3):
            paper = next(search_query)
            papers.append(paper)
    except StopIteration:
        pass
    return papers


def search_dblp(title, authors=None):
    """Searches for the paper on DBLP using title and authors."""
    query = title
    if authors:
        # Extract author's last name
        authors_last_name = [author.split()[-1] for author in authors]

        # Include authors in the query to improve accuracy
        author_query = ' '.join(authors_last_name)
        query += ' ' + author_query
    url = f'https://dblp.org/search/publ/api?q={requests.utils.quote(query)}&format=json'
    response = requests.get(url)
    data = response.json()
    hits = data.get('result', {}).get('hits', {}).get('hit', [])

    def read_authors(authors_raw):
        if not authors_raw:
            return ''
        if not isinstance(authors_raw, list):
            authors_raw = [authors_raw]
        authors = []
        for author in authors_raw:
            author_name = author.get('text', '') if isinstance(author, dict) else author
            author_name_clean = re.sub(r'\s+\d{4}$', '', author_name)
            authors.append(author_name_clean)
        return authors

    def read_title(title_raw):

        title = re.sub(r'\s+', ' ', title_raw).strip()

        # remove trailing period
        if title.endswith('.'):
            title = title[:-1]

        return title

    if hits:
        # Attempt to find an exact match
        for hit in hits:
            info = hit.get('info', {})
            hit_title = read_title(info.get('title'))
            hit_authors = read_authors(info.get('authors', {}).get('author', []))
            hit_authors_last_names = [author.split()[-1] for author in hit_authors]

            if hit_title.lower() == title.lower() and set(hit_authors_last_names) == set(authors_last_name):
                return {
                    'title': hit_title,
                    'authors': hit_authors,
                    'venue': info.get('venue'),
                    'year': info.get('year'),
                    'url': info.get('ee')
                }

        # Return the first hit if no exact match is found
        info = hits[0].get('info', {})
        return {
            'title': read_title(info.get('title')),
            'authors': read_authors(info.get('authors', {}).get('author', [])),
            'venue': info.get('venue'),
            'year': info.get('year'),
            'url': info.get('ee')
        }
    else:
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


def read_table(filename):
    """Reads the markdown table from the file and returns entries and headers."""
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # Find the start of the table
    table_start = None
    for i, line in enumerate(lines):
        if line.strip().startswith('|') and 'Title' in line:
            table_start = i
            break

    if table_start is None:
        print(f"No table found in '{filename}'.")
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
        entries.append(entry)
    return entries, headers


def write_table(filename, entries, headers):
    """Writes the list of dictionaries to the markdown file, updating only the table."""
    with open(filename, 'r', encoding='utf-8') as f:
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
        print(f"No table found in '{filename}'. Cannot write table.")
        return

    # Find the end of the table
    for j in range(table_start + 1, len(lines)):
        if not lines[j].strip().startswith('|'):
            table_end = j
            break
    else:
        table_end = len(lines)

    # Build the table content
    table_lines = []
    table_lines.append('| ' + ' | '.join(headers) + ' |')
    table_lines.append('| ' + ' | '.join(['---'] * len(headers)) + ' |')
    for entry in entries:
        row_values = []
        for h in headers:
            value = entry.get(h, '')
            if isinstance(value, list):
                # Convert list to string by joining with commas
                value_str = ', '.join(str(v) for v in value)
            else:
                value_str = str(value)
            value_str = value_str.replace('|', '\\|')
            row_values.append(value_str)
        row = '| ' + ' | '.join(row_values) + ' |'
        table_lines.append(row)

    # Replace the old table with the new table content
    new_lines = lines[:table_start] + table_lines + lines[table_end:]

    new_content = '\n'.join(new_lines)

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(new_content)


def add_reference(filename, title, existing_entry=None, ask_user=False):
    """Adds a reference to the bibliography markdown file."""
    # First, search the paper on Google Scholar

    print(f"Searching on Google Scholar...")

    papers = search_google_scholar(title)
    if not papers:
        print(f"No results found on Google Scholar.")
        return
    elif len(papers) == 1:
        selected_paper = papers[0]
    elif ask_user:
        # Prompt the user to choose one
        print(f"Multiple papers found on Google Scholar:")
        for idx, paper in enumerate(papers):
            paper_title = paper['bib'].get('title', 'No title')
            paper_authors = paper['bib'].get('author', 'No authors')
            if isinstance(paper_authors, list):
                paper_authors_str = paper_authors[0] + ' et al.'
            else:
                paper_authors_str = paper_authors
            print(f"    {idx + 1}. {paper_title} by {paper_authors_str}")
        try:
            choice = int(input(f"Please select the correct paper (1-{len(papers)}) or 0 to cancel: "))
            if choice == 0:
                return
            elif 1 <= choice <= len(papers):
                selected_paper = papers[choice - 1]
            else:
                return
        except ValueError:
            return
    else:
        selected_paper = papers[0]

    # Extract title and authors
    paper_title = selected_paper['bib'].get('title', '')
    paper_authors_data = selected_paper['bib'].get('author', '')
    if isinstance(paper_authors_data, str):
        paper_authors = [author.strip() for author in re.split(' and ', paper_authors_data)]
    elif isinstance(paper_authors_data, list):
        paper_authors = [author.strip() for author in paper_authors_data]
    else:
        paper_authors = []

    # Search on DBLP using the title and authors
    print(f"Searching on DBLP...")
    metadata = search_dblp(paper_title, paper_authors)
    if not metadata:
        return

    # Get citation count
    citation_count = selected_paper.get('num_citations', 0)

    # Generate summary using the abstract from Google Scholar
    abstract = selected_paper['bib'].get('abstract', '')
    print(f"Generating summary using ChatGPT...")
    summary = generate_summary(abstract) if abstract else "No abstract available."
    # Get URLs
    pub_url = selected_paper.get('pub_url', '')

    print(f"Searching on arXiv...")
    arxiv_url = search_arxiv(paper_title, paper_authors)

    # Build the URL cell content
    url_cell = ''
    if pub_url:
        url_cell += f"[link]({pub_url})"
    if arxiv_url:
        if url_cell:
            url_cell += ' '
        url_cell += f"[arXiv]({arxiv_url})"

    if not url_cell:
        # Use metadata URL if available
        metadata_url = metadata.get('url', '')
        if metadata_url:
            if isinstance(metadata_url, list):
                metadata_url = metadata_url[0]
            url_cell = f"[link]({metadata_url})"
        else:
            url_cell = "No URL available"

    # Get Google Scholar URL
    gs_url = f"https://scholar.google.com/scholar?q={requests.utils.quote(paper_title)}"

    # Build Citation Count cell with link to Google Scholar page
    citation_cell = f"[{citation_count}]({gs_url})"

    # Read existing entries and headers
    entries, headers = read_table(filename)

    # Prepare the reference entry as a dictionary
    entry = {
        'Title': metadata['title'],
        'Authors': metadata['authors'],
        'Publication': metadata['venue'],
        'Year': metadata['year'],
        'URL': url_cell,
        'Citation Count': citation_cell,
        'Summary': summary,
    }

    # If existing_entry is provided, preserve extra columns
    if existing_entry:
        for h in headers:
            if h not in entry:
                entry[h] = existing_entry.get(h, '')

    # Ensure all headers are present in the entry
    for h in headers:
        if h not in entry:
            entry[h] = ''

    # Add the new entry
    entries.append(entry)

    # Write back the table
    write_table(filename, entries, headers)

    print(f"Reference '{metadata['title']}' added to '{filename}'")


def update_references(filename):
    """Updates the references in the bibliography markdown file."""
    entries, headers = read_table(filename)
    for entry in entries:
        title = entry.get('Title', '')
        if not title:
            continue
        print(f"Updating '{title}'...")
        # Remove the reference
        remove_reference(filename, title)
        # Re-add the reference, preserving existing entry for extra columns
        add_reference(filename, title, existing_entry=entry)
    print(f"References in '{filename}' have been updated.")


def remove_reference(filename, title):
    """Removes a reference from the bibliography markdown file."""
    # Read existing entries and headers
    entries, headers = read_table(filename)

    # Find the entry to remove
    new_entries = [entry for entry in entries if entry.get('Title', '') != title]

    if len(entries) == len(new_entries):
        print(f"Reference '{title}' not found in '{filename}'.")
        return

    # Write back the table
    write_table(filename, new_entries, headers)
    print(f"Reference '{title}' removed from '{filename}'.")


def generate_bibtex(filename):
    """Generates a bibtex file from the bibliography markdown file."""
    entries, headers = read_table(filename)
    bibtex_entries = ""
    existing_keys = {}
    for entry in entries:
        title = entry.get('Title', '')
        authors = entry.get('Authors', '')
        venue = entry.get('Publication', '')
        year = entry.get('Year', '')
        url_cell = entry.get('URL', '')
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

    parser_new = subparsers.add_parser('new', help='Create a new bibliography database')
    parser_new.add_argument('filename', help='Markdown file name')

    parser_add = subparsers.add_parser('add', help='Add a reference')
    parser_add.add_argument('filename', help='Markdown file name')
    parser_add.add_argument('title', help='Paper title')

    parser_update = subparsers.add_parser('update', help='Update the references')
    parser_update.add_argument('filename', help='Markdown file name')

    parser_bibtex = subparsers.add_parser('bib', help='Generate a bibtex file')
    parser_bibtex.add_argument('filename', help='Markdown file name')

    args = parser.parse_args()

    if args.command == 'new':
        create_new_bibliography(args.filename)
    elif args.command == 'add':
        add_reference(args.filename, args.title, ask_user=True)
    elif args.command == 'update':
        update_references(args.filename)
    elif args.command == 'bib':
        generate_bibtex(args.filename)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
