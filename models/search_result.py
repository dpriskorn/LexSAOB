from typing import Dict

from pydantic import BaseModel


class SearchResult(BaseModel):
    base_url: str = "https://www.saob.se"
    href: str
    text: str
    id: str
    lexical_category: str
    # TODO update this list
    lexical_categories: Dict[str, str] = dict(
        adverbium="Q380057",
        sbst="Q1084",
        adjektiv="Q34698",
        udråbsord="Q83034",
        verbum="Q24905",
        konjunktion="Q36484",
        suffiks="Q102047",
        præfiks="Q134830",
        talord="Q63116",
    )

    @property
    def lexical_category_qid(self) -> str:
        """Match using self.lexical_categories"""
        qid = self.lexical_categories.get(self.lexical_category)
        if qid is None:
            raise ValueError(f"No QID found for lexical category '{self.lexical_category}'")
        return qid

    @property
    def url(self) -> str:
        return self.base_url + self.href
