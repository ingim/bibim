from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass
class Reference(abc.ABC):
    author: str
    title: str
    year: str
    url: str | None

    @property
    def author_last_names(self) -> list[str]:
        return [a.strip().split()[-1] for a in self.author.split(',')]

    @property
    def author_concise(self):
        return [
            "".join([n[0].upper() for n in a.split()[:-1]]) + " " + a.split()[-1]
            for a in self.author.split(',')
        ]

    def __eq__(self, other):
        if self.title.lower() != other.title.lower():
            return False

        for a1, a2 in zip(self.author_last_names, other.author_last_names):
            if a1.lower() != a2.lower():
                return False

        return True

    @abc.abstractmethod
    def to_bibtex(self, key: str) -> str:
        ...


@dataclass
class Article(Reference):
    journal: str
    volume: str | None
    doi: str | None
    arxiv: str | None
    num_citations: str | None

    def to_bibtex(self, key: str) -> str:
        res = f"@article{{{key},\n"
        res += f"    author = {{{self.author}}},\n"
        res += f"    title = {{{self.title}}},\n"
        res += f"    journal = {{{self.journal}}},\n"
        res += f"    year = {{{self.year}}},\n"
        if self.url:
            res += f"    url = {{{self.url}}},\n"
        if self.volume:
            res += f"    volume = {{{self.volume}}},\n"
        if self.doi:
            res += f"    doi = {{{self.doi}}},\n"
        if self.arxiv:
            res += f"    arxiv = {{{self.arxiv}}},\n"
        res += "}\n"

        return res


@dataclass
class Proceedings(Reference):
    booktitle: str
    publisher: str
    doi: str | None
    arxiv: str | None
    num_citations: str | None

    def to_bibtex(self, key: str) -> str:
        res = f"@inproceedings{{{key},\n"
        res += f"    author = {{{self.author}}},\n"
        res += f"    title = {{{self.title}}},\n"
        res += f"    booktitle = {{{self.booktitle}}},\n"
        res += f"    year = {{{self.year}}},\n"
        res += f"    publisher = {{{self.publisher}}},\n"
        if self.url:
            res += f"    url = {{{self.url}}},\n"
        if self.doi:
            res += f"    doi = {{{self.doi}}},\n"
        if self.arxiv:
            res += f"    arxiv = {{{self.arxiv}}},\n"
        res += "}\n"

        return res


@dataclass
class Misc(Reference):
    note: str | None

    def to_bibtex(self, key: str) -> str:
        res = f"@misc{{{key},\n"
        res += f"    author = {{{self.author}}},\n"
        res += f"    title = {{{self.title}}},\n"
        res += f"    year = {{{self.year}}},\n"
        if self.url:
            res += f"    url = {{{self.url}}},\n"
        if self.note:
            res += f"    note = {{{self.note}}},\n"
        res += "}\n"

        return res


class Paper:
    title: str
    author: str
    year: str
    venue: str
    url: str
    arxiv_id: str
    abstract: str
    num_citations: str

    def __init__(self,
                 title: str,
                 author: str,
                 year: str | None = None,
                 venue: str | None = None,
                 url: str | None = None,
                 arxiv_id: str | None = None,
                 abstract: str | None = None,
                 num_citations: str | None = None):
        self.title = title
        self.author = author
        self.year = year
        self.venue = venue
        self.url = url
        self.arxiv_id = arxiv_id
        self.abstract = abstract
        self.num_citations = num_citations

    @staticmethod
    def from_page_entry(entry: dict) -> Paper:
        return Paper(
            title=entry['title'],
            author=entry['authors'],
            year=entry['year'],
            venue=entry['venue'],
            url=entry['url'],
            arxiv_id=entry['arxiv_id'],
            abstract=entry['abstract'],
            num_citations=entry['num_citations'],
        )

    def to_page_entry(self) -> dict:
        return {
            "title": self.title,
            "authors": self.author,
            "venue": self.venue,
            "year": self.year,
            "abstract": self.abstract,
            "arxiv_id": f"[{self.arxiv_id}]({self.arxiv_id})" if self.arxiv_id else "",
            "url": f"[{self.url}]({self.url})" if self.url else "",
            "num_citations": self.num_citations,
        }
