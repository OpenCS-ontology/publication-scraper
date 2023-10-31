import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Set, Optional, List

from urllib.parse import quote


_SCRAPER_DEST_DIR = str(os.environ.get("SCRAPER_DEST_DIR"))


def format_strings(target: str) -> str:
    """
    Format strings into a serializable form, for example, to be used as objects in a vocabulary.
    """
    return quote(target.replace(" ", "_").replace(",", "").strip(".").replace("/", "-"))


class IdEquivalent(ABC):
    @abstractmethod
    def get_id(self) -> str:
        raise NotImplementedError

    def __eq__(self, other):
        return isinstance(other, self.__class__) and self.get_id() == other.get_id()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.get_id())


@dataclass(eq=False)
class Conference:
    name: str = None


@dataclass(eq=False)
class Journal:
    name: str = None
    website: str = None


@dataclass(eq=False)
class Manifestation:
    has_url: str = None
    format: str = None


@dataclass(eq=False)
class AffiliationModel:
    name: str

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return self.name == other.name

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.name)

    def get_id(self):
        return format_strings(self.name)


@dataclass(eq=False)
class AuthorModel(IdEquivalent):
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    name: str = None
    orcid: Optional[str] = None
    affiliations: Set[AffiliationModel] = None

    def get_id(self) -> str:
        if self.orcid is not None:
            return self.orcid
        elif self.given_name is not None and self.family_name is not None:
            return format_strings(self.given_name + " " + self.family_name)
        else:
            return format_strings(self.name)


@dataclass(eq=False)
class PaperModel(IdEquivalent):
    doi: str = None
    abstract_text: Optional[str] = None
    keywords: Set[str] = None
    url: str = None
    pdf_url: str = None
    title: str = None
    volume: str = None
    startingPage: str = None
    endingPage: str = None
    date_created: str = None
    authors: Set[AuthorModel] = None
    issn: str = None
    page_count: str = None
    publication_date: str = None
    source: str = None
    license: str = None
    language: str = None
    publisher: str = None
    manifestation: Manifestation = None
    journal: Journal = None
    conference: Conference = None
    additional_type: str = None
    paper_type: str = None

    def get_id(self):
        return (
            "SCPE_"
            + ((self.volume + "_") if self.volume is not None else "")
            + format_strings(self.title)
        )


class DataModel:
    def __init__(self, filename: str):
        self._id = filename
        self._papers: Set[PaperModel] = set()
        self._authors: Set[AuthorModel] = set()
        self._affiliations: Set[AffiliationModel] = set()

    def add_paper(self, paper: PaperModel):
        self._papers.add(paper)
        for author in paper.authors:
            if author not in self._authors:
                self.add_author(author)

    def add_author(self, author: AuthorModel):
        self._authors.add(author)
        for affiliation in author.affiliations:
            if affiliation not in self._affiliations:
                self.add_affiliation(affiliation)

    def add_affiliation(self, affiliation: AffiliationModel):
        self._affiliations.add(affiliation)
