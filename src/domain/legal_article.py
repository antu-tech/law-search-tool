from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class LegalArticle:
    law_name: str
    article_number: str
    text: str
    keywords: List[str]
