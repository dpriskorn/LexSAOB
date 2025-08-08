import logging
import random
from typing import List

from pydantic import BaseModel
from requests import Session
from wikibaseintegrator import WikibaseIntegrator
from wikibaseintegrator.wbi_helpers import execute_sparql_query
from wikibaseintegrator.wbi_login import Login

import config
from models.wikidata.lexeme import SaobLexeme

logger = logging.getLogger(__name__)


class SaobMatcher(BaseModel):
    lexemes: List[SaobLexeme] = list()
    session: Session = Session()

    class Config:
        arbitrary_types_allowed = True

    def fetch_lexemes_without_saob_id(self):
        """download all swedish lexemes via sparql (~23000 as of 2021-04-05)"""
        wbi = WikibaseIntegrator(
            login=Login(user=config.user_name, password=config.bot_password)
        )
        # dictionary with word as key and list in the value
        # list[0] = lid
        # list[1] = category Qid
        if config.lexeme_fetch_limit > 0:
            print(f"Fetching {config.lexeme_fetch_limit} lexemes")
            limit = config.lexeme_fetch_limit
        else:
            print("Fetching all lexemes")
            limit = 30000
        # lexemes_data = {}
        # lexeme_lemma_list = []
        offset = random.randint(a=0, b=20000)
        # print(f"Using offset {offset}")
        results = execute_sparql_query(f"""
                select ?lexemeId ?lemma ?category
            WHERE {{
              #hint:Query hint:optimizer "None".
              ?lexemeId dct:language wd:Q9027;
                        wikibase:lemma ?lemma;
                        wikibase:lexicalCategory ?category.
              MINUS{{
                ?lexemeId wdt:P8478 [].
              }}
              MINUS{{
                ?lexemeId wdt:P9963 [].
              }}
              MINUS {{
                # Exclude truthy no value statements
                ?lexemeId a wdno:P8478.                  
              }}
              MINUS {{
                # Exclude truthy no value statements
                ?lexemeId a wdno:P9963.                  
              }}
            }}
            limit {limit}
            #offset {offset}
            """)
        if len(results) == 0:
            print("No lexemes found")
        else:
            # print("adding lexemes to list")
            # pprint(results.keys())
            # pprint(results["results"].keys())
            # pprint(len(results["results"]["bindings"]))
            for result in results["results"]["bindings"]:
                # print(result)
                # *************************
                # Handle result and upload
                # *************************
                lemma = result["lemma"]["value"]
                lid = result["lexemeId"]["value"].replace(config.wd_prefix, "")
                lexical_category = result["category"]["value"].replace(config.wd_prefix, "")
                self.lexemes.append(SaobLexeme(
                    id=lid,
                    lemma=lemma,
                    lexical_category=lexical_category,
                    wbi=wbi,
                    session=self.session
                ))
        print(f"{len(self.lexemes)} lexemes fetched")

    def run(self):
        logger.debug("lookup_labels: running")

        for lexeme in self.lexemes:
            lexeme.match_and_improve()


    # def get_content_from_html(self, response):
    #     raise NotImplementedError("update to SAOB")
    #     div_bogspalte_strainer = SoupStrainer('div', class_='bogspalte')
    #     # Parse only the parts of the document that match the strainer
    #     soup = BeautifulSoup(response.text, "lxml", parse_only=div_bogspalte_strainer)
    #
    #     bogspalte_div = soup.find('div', class_='bogspalte')
    #     artikelkilde_div = bogspalte_div.find('div', class_='artikelkilde')
    #
    #     if artikelkilde_div:
    #         artikelkilde_div.decompose()
    #
    #     print(bogspalte_div)
