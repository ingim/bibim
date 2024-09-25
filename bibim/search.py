import re

import requests
import feedparser
from scholarly import scholarly

def search_paper(title: str, ask_user: bool = False) -> Paper | None:
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
            paper_authors_str = paper.author[0].full_name + (' et al.' if len(paper.author) > 1 else '')
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
    dblp_paper = search_dblp(google_paper.title, google_paper.author)

    if not dblp_paper:
        print(f"No results found on DBLP.")
        return

    # Step 4. Search on arXiv using the title and authors
    print(f"Searching on arXiv...")
    arxiv_paper = search_arxiv(google_paper.title, google_paper.author)

    # Step 5. Consolidate the metadata
    paper = Paper(
        title=dblp_paper.title,
        authors=dblp_paper.author,
        year=dblp_paper.year,
        venue=dblp_paper.venue,
        url=dblp_paper.url,
        arxiv_id=arxiv_paper.arxiv_id if arxiv_paper else None,
        abstract=google_paper.abstract,
        num_citations=google_paper.num_citations
    )

    return paper


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
                    if paper.author[0].last_name.lower() != authors[0].last_name.lower():
                        continue
                return paper

    print(f"No results found for '{title}' on DBLP.")
    return None
