import json
import logging
import re
from enum import Enum
from pprint import pprint
from typing import List, Union

import requests
from bs4 import BeautifulSoup


class SAOBSubentry:
    """Lemmas are listed as subentries on entries they
    share a head word with:
    E.g. handuk is on the SAOBEntry "hand" under "-duk"

    Each subentry has a section_id and can be
    easily linked to using the seek_parameter
    and section_id :)
    """
    seek_parameter: str = None  # This is a url-escaped string
    section_id: str = None
    lemma: str

    def __init__(self, lemma: str):
        if lemma is None:
            raise Exception("lemma was None")
        self.lemma = lemma

    def __str__(self):
        return (f"SAOBSubentry: "
                f"lemma:{self.lemma} "
                f"entry_lemma:{self.seek_parameter} "
                f"section_id:{self.section_id}")

    # def search_for_lemma(self):
    #     """Search for a given lemma in SAOB
    #     and populate self.entry_id"""
    #     logger = logging.getLogger(__name__)
    #     response = requests.get(self.search_url())
    #     logger.debug(response.headers)
    #     soup = BeautifulSoup(response.text, 'html.parser')
    #     not_found = soup.select_one(".alert-block")
    #     if not_found:
    #         return False
    #     else:
    #         raise Exception(f"Could not parse response, see {self.search_url()}")

    def search_using_api(self):
        logger = logging.getLogger(__name__)
        header = {
            "Accept": "application/json",
        }
        response = requests.get(
            ("https://www.saob.se/wp-admin/admin-ajax.php?"
             f"action=myprefix_autocompletesearch&term={self.lemma}"),
            headers=header
        )
        if response.status_code == 200:
            logger.debug("Got 200")
            # Clean the JSON. It has () around it
            data = response.text.strip().replace('(', '').replace(')', '')
            suggestions = json.loads(data)
            # pprint(suggestions)
            # We get a list back from the API with suggestions
            for suggestion in suggestions:
                # Clean away the dash
                label = suggestion["label"].replace("-", "")
                link = suggestion["link"]
                if label == self.lemma:
                    logger.debug("We found a matching subentry!")
                    pattern = "\/artikel\/\?seek=([\w%]+)&pz=\d#([A-Z]\w+)"
                    matches: Union[List[tuple], None] = re.findall(pattern, link)
                    logger.debug(f"matches:{matches} for {link}")
                    # Check if we got a section_id:
                    if matches is not None:
                        self.seek_parameter = matches[0][0]
                        self.section_id = matches[0][1]
                        logger.info(self)
                        print(self.url())
                        return True
                else:
                    logger.debug(f"Skipped {label}")
            # No match found for any of the suggestions
            return False
        else:
            raise Exception(f"Got {response.status_code} from SAOB.se")

    def search_url(self):
        try:
            return f"https://www.saob.se/artikel/?seek={self.lemma}"
        except:
            pass
            #raise AttributeError("no lemma")

    def url(self):
        try:
            return f"https://www.saob.se/artikel/?seek={self.seek_parameter}#{self.section_id}"
        except:
            pass


class SAOBEntry():
    id: str = None
    lemma: str = None
    lexical_category: str = None
    number: int = None

    def __init__(self,
                 id: str = None,
                 lemma: str = None,
                 lexical_category: str = None,
                 number: int = None):
        self.id = id
        self.lemma = lemma
        self.lexical_category = lexical_category
        self.number = number

    def scrape_details(self):
        """Scrape details from SAOB"""
        pass

    def url(self):
        return f"https://www.saob.se/artikel/?unik={self.id}"
