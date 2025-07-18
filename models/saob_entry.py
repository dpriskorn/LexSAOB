import json
import logging
import re
from enum import Enum
from pprint import pprint
from typing import List, Union

import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel


class SAOBEntry(BaseModel):
    id: str = ""
    lemma: str = ""
    lexical_category: str = ""
    number: int = 0

    def scrape_subentries(self):
        """Scrape details from SAOB"""
        pass

    def url(self):
        return f"https://www.saob.se/artikel/?unik={self.id}"
