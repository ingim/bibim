import re
from dataclasses import dataclass

import requests
import feedparser
from scholarly import scholarly

from .reference import Reference


# first author last name
def faln(author: str) -> str:
    return author.split(',')[0].split()[-1].strip()


def search_reference(title: str, ask_user: bool = False) -> Reference | None:
    # Step 1. Search on Google Scholar
    print(f"Searching on Google Scholar...")
    results = search_google_scholar(title)
    if not results:
        print(f"No results found on Google Scholar.")
        return
    elif len(results) == 1:
        google_result = results[0]
    elif ask_user:
        # Prompt the user to choose one
        print(f"Multiple papers found on Google Scholar:")
        for idx, result in enumerate(results):
            print(f"    {idx + 1}. {result.title} by {faln(result.author_concise)} et al.")
        try:
            choice = int(input(f"Please select the correct paper (1-{len(results)}) or 0 to cancel: "))
            if choice == 0:
                return
            elif 1 <= choice <= len(results):
                google_result = results[choice - 1]
            else:
                return
        except ValueError:
            return
    else:
        google_result = results[0]

    # Step 3. Search on DBLP using the title and authors
    print(f"Searching on DBLP...")
    dblp_results = search_dblp(google_result.title + ' ' + faln(google_result.author_concise))

    # find best matching results
    dblp_result = None
    for result in dblp_results:
        if result.title.lower() == google_result.title.lower() and faln(result.author).lower() == faln(google_result.author_concise).lower():
            dblp_result = result
            break

    if dblp_result is None:
        print(f"No results found on DBLP.")

    # get bibtex
    bibtex, bibtex_condensed = parse_dblp_bibtex(dblp_result.dblp_url)

    # Step 4. Search on arXiv using the title and authors
    print(f"Searching on arXiv...")
    arxiv_results = search_arxiv(google_result.title + ' ' + faln(google_result.author_concise))

    # find best matching results
    arxiv_result = None
    for result in arxiv_results:
        if result.title.lower() == google_result.title.lower() and faln(result.author).lower() == faln(google_result.author_concise).lower():
            arxiv_result = result
            break

    if dblp_result is None:

        return Reference(
            author=google_result.author_concise,
            title=google_result.title,
            year=None,
            bibtex=bibtex,
            bibtex_condensed=bibtex_condensed,
            venue=None,
            url=google_result.pub_url,
            num_citations=google_result.num_citations,
        )

    else:

        # Step 5. Consolidate the metadata
        return Reference(
            author=dblp_result.author,
            title=dblp_result.title,
            year=dblp_result.year,
            bibtex=bibtex,
            bibtex_condensed=bibtex_condensed,
            venue=dblp_result.venue,
            url=arxiv_result.arxiv_id if arxiv_result else google_result.pub_url,
            num_citations=google_result.num_citations,
        )


@dataclass
class ArXivResult:
    author: str
    title: str
    arxiv_id: str
    summary: str


def search_arxiv(query: str, max_results: int = 1) -> list[ArXivResult]:
    """Searches arXiv for the paper title and authors' last names, returns the arXiv URL if found."""
    query = f"ti:\"{query}\""
    url = f"https://export.arxiv.org/api/query?search_query={requests.utils.quote(query)}&max_results={max_results}"
    response = requests.get(url)
    if response.status_code != 200:
        print("Error accessing arXiv API.")
        return []
    feed = feedparser.parse(response.content)

    # Example of a search result:
    # {'id': 'http://arxiv.org/abs/2311.04934v2', 'guidislink': True, 'link': 'http://arxiv.org/abs/2311.04934v2',
    #  'updated': '2024-04-25T15:45:19Z',
    #  'updated_parsed': time.struct_time(tm_year=2024, tm_mon=4, tm_mday=25, tm_hour=15, tm_min=45, tm_sec=19, tm_wday=3,
    #                                     tm_yday=116, tm_isdst=0), 'published': '2023-11-07T18:17:05Z',
    #  'published_parsed': time.struct_time(tm_year=2023, tm_mon=11, tm_mday=7, tm_hour=18, tm_min=17, tm_sec=5, tm_wday=1,
    #                                       tm_yday=311, tm_isdst=0),
    #  'title': 'Prompt Cache: Modular Attention Reuse for Low-Latency Inference',
    #  'title_detail': {'type': 'text/plain', 'language': None, 'base': '',
    #                   'value': 'Prompt Cache: Modular Attention Reuse for Low-Latency Inference'},
    #  'summary': 'We present Prompt Cache, an approach for accelerating inference for large\nlanguage models (LLM) by reusing attention states across different LLM prompts.\nMany input prompts have overlapping text segments, such as system messages,\nprompt templates, and documents provided for context. Our key insight is that\nby precomputing and storing the attention states of these frequently occurring\ntext segments on the inference server, we can efficiently reuse them when these\nsegments appear in user prompts. Prompt Cache employs a schema to explicitly\ndefine such reusable text segments, called prompt modules. The schema ensures\npositional accuracy during attention state reuse and provides users with an\ninterface to access cached states in their prompt. Using a prototype\nimplementation, we evaluate Prompt Cache across several LLMs. We show that\nPrompt Cache significantly reduce latency in time-to-first-token, especially\nfor longer prompts such as document-based question answering and\nrecommendations. The improvements range from 8x for GPU-based inference to 60x\nfor CPU-based inference, all while maintaining output accuracy and without the\nneed for model parameter modifications.',
    #  'summary_detail': {'type': 'text/plain', 'language': None, 'base': '',
    #                     'value': 'We present Prompt Cache, an approach for accelerating inference for large\nlanguage models (LLM) by reusing attention states across different LLM prompts.\nMany input prompts have overlapping text segments, such as system messages,\nprompt templates, and documents provided for context. Our key insight is that\nby precomputing and storing the attention states of these frequently occurring\ntext segments on the inference server, we can efficiently reuse them when these\nsegments appear in user prompts. Prompt Cache employs a schema to explicitly\ndefine such reusable text segments, called prompt modules. The schema ensures\npositional accuracy during attention state reuse and provides users with an\ninterface to access cached states in their prompt. Using a prototype\nimplementation, we evaluate Prompt Cache across several LLMs. We show that\nPrompt Cache significantly reduce latency in time-to-first-token, especially\nfor longer prompts such as document-based question answering and\nrecommendations. The improvements range from 8x for GPU-based inference to 60x\nfor CPU-based inference, all while maintaining output accuracy and without the\nneed for model parameter modifications.'},
    #  'authors': [{'name': 'In Gim'}, {'name': 'Guojun Chen'}, {'name': 'Seung-seob Lee'}, {'name': 'Nikhil Sarda'},
    #              {'name': 'Anurag Khandelwal'}, {'name': 'Lin Zhong'}], 'author_detail': {'name': 'Lin Zhong'},
    #  'author': 'Lin Zhong', 'arxiv_comment': 'To appear at MLSys 2024',
    #  'links': [{'href': 'http://arxiv.org/abs/2311.04934v2', 'rel': 'alternate', 'type': 'text/html'},
    #            {'title': 'pdf', 'href': 'http://arxiv.org/pdf/2311.04934v2', 'rel': 'related', 'type': 'application/pdf'}],
    #  'arxiv_primary_category': {'term': 'cs.CL', 'scheme': 'http://arxiv.org/schemas/atom'},
    #  'tags': [{'term': 'cs.CL', 'scheme': 'http://arxiv.org/schemas/atom', 'label': None},
    #           {'term': 'cs.AI', 'scheme': 'http://arxiv.org/schemas/atom', 'label': None}]}

    results = []
    for entry in feed.entries:
        arxiv_id = entry.get('id', '')

        # Ensure that the title matches
        title = entry.get('title', '')

        author = ', '.join([a.name for a in entry.get('authors', [])])
        summary = entry.get('summary', '')

        results.append(ArXivResult(
            author=author,
            title=title,
            arxiv_id=arxiv_id,
            summary=summary
        ))
    return results


@dataclass
class GoogleScholarResult:
    author_concise: str
    title: str
    num_citations: str
    pub_url: str


def search_google_scholar(query: str, max_results: int = 3) -> list[GoogleScholarResult]:
    """Searches for the paper title on Google Scholar and returns matching papers."""
    search_query = scholarly.search_pubs(query)
    results = []

    # Example of a search result:
    # {
    #     'container_type': 'Publication',
    #     'bib': {
    #         'title': 'Fastformer: Additive attention can be all you need',
    #         'author': ['C Wu', 'F Wu', 'T Qi', 'Y Huang', 'X Xie'],
    #         'pub_year': '2021', 'venue': 'arXiv preprint arXiv:2108.09084',
    #         'abstract': 'attention. In Fastformer, instead of modeling the pair-wise intractions between tokens, we first  use additive attention mecha • We propose an additive attention based Transformer named'
    #     },
    #     'filled': False,
    #     'gsrank': 4,
    #     'pub_url': 'https://arxiv.org/abs/2108.09084',
    #     'author_id': [
    #         'OG1cMswAAAAJ', '0SZVO0sAAAAJ', 'iRr7c9wAAAAJ', '', '5EQfAFIAAAAJ'],
    #     'url_scholarbib': '/scholar?hl=en&q=info:9_kFeQ_sO-wJ:scholar.google.com/&output=cite&scirp=3&hl=en',
    #     'url_add_sclib': '/citations?hl=en&xsrf=&continue=/scholar%3Fq%3Dattention%2Bis%2Ball%2Byou%2Bneed%26hl%3Den%26as_sdt%3D0,33&citilm=1&update_op=library_add&info=9_kFeQ_sO-wJ&ei=jlj0ZqXHLsye6rQPjviW2A4&json=',
    #     'num_citations': 145,
    #     'citedby_url': '/scholar?cites=17022458767776020983&as_sdt=5,33&sciodt=0,33&hl=en',
    #     'url_related_articles': '/scholar?q=related:9_kFeQ_sO-wJ:scholar.google.com/&scioq=attention+is+all+you+need&hl=en&as_sdt=0,33',
    #     'eprint_url': 'https://arxiv.org/pdf/2108.09084'
    # }

    try:
        for _ in range(max_results):
            paper = next(search_query)

            results.append(GoogleScholarResult(
                author_concise=', '.join(paper['bib'].get('author', '')),
                title=paper['bib'].get('title', '').strip(),
                num_citations=str(paper.get('num_citations', 0)),
                pub_url=paper.get('pub_url', '')
            ))
    except StopIteration:
        pass

    return results


@dataclass
class DBLPResult:
    author: str
    title: str
    venue: str
    year: str
    dblp_url: str


def search_dblp(query: str) -> list[DBLPResult]:
    """Searches for the paper on DBLP using title and authors."""

    url = f'https://dblp.org/search/publ/api?q={requests.utils.quote(query)}&format=json'
    response = requests.get(url)
    data = response.json()
    hits = data.get('result', {}).get('hits', {}).get('hit', [])

    if not hits:
        return []

    results = []

    # Attempt to find an exact match
    for entry in hits:

        # Example of a search result:
        # {
        #     '@score': '8',
        #     '@id': '323951',
        #     'info':
        #         {
        #             'authors': {
        #                 'author': [
        #                     {'@pid': '375/1509', 'text': 'Georgy Tyukin'},
        #                     {'@pid': '342/2924', 'text': 'Gbètondji J.-S. Dovonon'},
        #                     {'@pid': '232/9592', 'text': 'Jean Kaddour'},
        #                     {'@pid': '58/10142', 'text': 'Pasquale Minervini'}]},
        #             'title': 'Attention Is All You Need But You Don&apos;t Need All Of It For Inference of Large Language Models.',
        #             'venue': 'CoRR', 'volume': 'abs/2407.15516', 'year': '2024',
        #             'type': 'Informal and Other Publications', 'access': 'open',
        #             'key': 'journals/corr/abs-2407-15516', 'doi': '10.48550/ARXIV.2407.15516',
        #             'ee': 'https://doi.org/10.48550/arXiv.2407.15516',
        #             'url': 'https://dblp.org/rec/journals/corr/abs-2407-15516'},
        #     'url': 'URL#323951'
        # }

        author_list = entry["info"]["authors"]["author"]
        if isinstance(author_list, dict):
            author_list = [author_list]

        def author_name_clean(author_name: str) -> str:
            return re.sub(r'\s+\d{4}$', '', author_name)

        author = ','.join([author_name_clean(author["text"]) for author in author_list])

        title = entry["info"]["title"].strip()
        if title[-1] == '.':
            title = title[:-1]

        results.append(DBLPResult(
            author=author,
            title=title,
            venue=entry["info"]["venue"],
            year=entry["info"]["year"],
            dblp_url=entry["info"]["url"]
        ))

    return results


def replace_bibtex_key(bibtex_entry: str, new_key: str) -> str:
    # Pattern to match the key in a BibTeX entry
    pattern = r'(@\w+\{\s*)(.*?)(\s*,)'

    # Function to replace the key
    def replacer(match):
        return match.group(1) + new_key + match.group(3)

    # Replace the old key with the new key
    new_bibtex_entry = re.sub(pattern, replacer, bibtex_entry, count=1)
    return new_bibtex_entry


def parse_dblp_bibtex(url: str, ) -> (str, str):
    bibtex = requests.get(f"{url}.bib?param=1").text
    bibtex_condensed = requests.get(f"{url}.bib?param=0").text

    # bibtex = replace_bibtex_key(bibtex, new_key)
    # bibtex_condensed = replace_bibtex_key(bibtex_condensed, new_key)

    return bibtex, bibtex_condensed
