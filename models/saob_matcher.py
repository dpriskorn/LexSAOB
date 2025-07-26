import logging
from pprint import pprint
from typing import List
from urllib.parse import quote

from bs4 import SoupStrainer, BeautifulSoup
from pydantic import BaseModel
from requests import Session
from wikibaseintegrator import WikibaseIntegrator
from wikibaseintegrator.entities import LexemeEntity
from wikibaseintegrator.models import Qualifiers
from wikibaseintegrator.datatypes import Item, Time
from wikibaseintegrator.wbi_helpers import execute_sparql_query
from wikibaseintegrator.wbi_login import Login

import config
from models.exceptions import FetchError
from models.search_result import SearchResult

logger = logging.getLogger(__name__)


class SaobMatcher(BaseModel):
    lids: List[str] = list()
    session: Session = Session()
    property_to_work_on: str = "P8478"  # SAOB entry
    dictionary_item: str = "Q1935308"  # SAOB
    query_format_url: str = "https://www.saob.se/artikel/?seek="

    class Config:
        arbitrary_types_allowed = True

    def download_lids(self):
        # query = f"""
        # SELECT ?lexeme WHERE {{
        #     ?lexeme dct:language wd:Q9027;
        #             wikibase:lemma ?lemma.
        #     FILTER NOT EXISTS {{
        #         ?lexeme wdt:{self.property_to_work_on} [].
        #         }}
        # }}
        # offset 100
        # limit 100
        # """
        # result = execute_sparql_query(query=query)
        # self.lids = [
        #     item["lexeme"]["value"].replace("http://www.wikidata.org/entity/", "")
        #     for item in result["results"]["bindings"]
        # ]
        # todo remove debug
        logging.warning("Debug hard-coded to 1 LID")
        self.lids = ["L579308"]

    @staticmethod
    def is_single_hit_in_saob(response) -> bool:
        # fixme update to saob
        raise NotImplementedError()

        only_div_tags = SoupStrainer("div")
        soup = BeautifulSoup(response.text, "lxml", parse_only=only_div_tags)
        # Select the first div with class 'diskret'
        first_diskret_div = soup.find("div", class_="diskret")

        # Get the text content inside the first div
        if first_diskret_div:
            text_inside_first_div = first_diskret_div.get_text()
            logger.debug(text_inside_first_div)
            if text_inside_first_div.strip() == "(1)":
                logger.debug("Content of the div is '(1)'")
                # todo add the id of this entry to wikidata
                return True
            else:
                logger.debug("Content of the div is not '(1)'")
                return False
        else:
            raise ValueError("No div with class 'diskret' found.")

    @staticmethod
    def get_match_url(response):
        raise NotImplementedError("update to SAOB")

        only_a_tags = SoupStrainer("a")
        soup = BeautifulSoup(response.text, "lxml", parse_only=only_a_tags)
        # Find the first anchor element with class 'searchMatch'
        return soup.find("a", class_="searchMatch")

    @staticmethod
    def get_saob_article_id(response) -> str:
        raise NotImplementedError("update to SAOB")
        from bs4 import SoupStrainer

        only_a_tags = SoupStrainer("a")
        soup = BeautifulSoup(response.text, "lxml", parse_only=only_a_tags)
        # Find the first anchor element with class 'searchMatch'
        # Find the anchor element with class 'fejlrapport'
        anchor = soup.find("a", class_="fejlrapport")

        # Extract the value of the href attribute
        if anchor:
            href_value = anchor.get("href")
            logger.debug(href_value)
            return href_value.split("(")[1].rstrip(")")
        else:
            raise ValueError("Anchor element not found.")

    @staticmethod
    def number_of_lexemes_with_identical_lemma_and_lexcat(lemma, lexcat) -> int:
        query = f"""
            SELECT (COUNT(?lexeme) as ?count) WHERE {{
                ?lexeme dct:language wd:Q9035;
                        wikibase:lemma "{lemma}"@da;
                        wikibase:lexicalCategory wd:{lexcat}.
            }}
        """
        data = execute_sparql_query(query)
        count = int(data["results"]["bindings"][0]["count"]["value"])
        logger.info(f"Found {count} lexemes with the same lemma and category in WD")
        return count

    @staticmethod
    def get_saob_lemma(response) -> str:
        raise NotImplementedError("update to SAOB")
        # FIXME adapt to SAOB
        # Create a custom soup strainer to filter elements by class
        strainer = SoupStrainer(class_="match")

        # Parse only the parts of the document that match the strainer
        soup = BeautifulSoup(response.text, "lxml", parse_only=strainer)

        # Find the span element with the class 'match' and extract its text
        span_match = soup.find("span", class_="match")
        logger.debug(span_match)
        if span_match:
            # Remove any span elements with the class 'super' inside the 'match' span
            for span_super in span_match.find_all("span", class_="super"):
                span_super.decompose()
            text = span_match.get_text()
            logger.debug(text)
            return text
        else:
            raise ValueError("Element with class 'match' not found")

    @staticmethod
    def enrich_wikidata(
        lexeme: LexemeEntity,
    ):
        # print(lexeme.get_entity_url())
        # pprint(self.item.get_json())
        if config.press_enter_to_continue:
            input("press enter to upload")
        lexeme.write(
            summary="Adding ODS identifier with [[Wikidata:Tools/LexODS|LexODS]]"
        )
        print(lexeme.get_entity_url())
        # if config.press_enter_to_continue:
        #     input("press enter to continue")

    def remove_not_found_in_saob_if_present(self, lexeme):
        try:
            not_found_in = lexeme.claims.get(property=self.property_to_work_on)
            for claim in not_found_in:
                logger.debug(claim.mainsnak.datavalue)
                # exit()
                if claim.mainsnak.datavalue["value"]["id"] == self.dictionary_item:
                    claim.remove()
                    print("Removed not found in -> SAOB statement")
                    input("press enter to continue")
            # This should cause the claim to be removed
        except KeyError:
            pass
        return lexeme

    def search_result_count(self, response) -> int:
        # Define the SoupStrainer to filter div tags with the specified class
        strainer = SoupStrainer('div', class_='alert alert-block')

        # Parse the HTML content with the strainer
        soup = BeautifulSoup(response.text, 'lxml', parse_only=strainer)

        # Extract the text content
        if soup.div:
            text_content = soup.div.get_text(strip=True)

            # Split the text and extract the first number
            numbers = [int(s) for s in text_content.split() if s.isdigit()]

            if numbers:
                first_number = numbers[0]
                # print("First number:", first_number)
                return first_number
            else:
                raise ValueError("No numbers found in the text.")
        else:
            raise ValueError("Div not found.")

    def is_search_result(self, response):
        # Define the SoupStrainer to filter only h2 tags
        strainer = SoupStrainer('h2')

        # Parse the HTML content with the strainer
        soup = BeautifulSoup(response.text, 'lxml', parse_only=strainer)

        # Find the first h2 element
        first_h2 = soup.find('h2')

        # Check if the first h2's text is equal to "Sökresultat"
        if first_h2 and first_h2.get_text(strip=True) == 'Sökresultat':
            return True
        else:
            return False

    def parse_search_results(self, response) -> List[SearchResult]:
        """ignore ↩ which is a redirect we dont care about

        the html looks like this
        <a class="titlez" href="/artikel/?unik=T_0915-0036.3pwB&amp;pz=3">test &nbsp;  <span class="caset">sbst. 2</span></a><br>
        <a class="titlez" href="/artikel/?unik=T_0915-0037.Ut0B&amp;pz=3">test &nbsp;  <span class="caset">sbst. 3</span></a><br>"""
        logger.debug("parsing search results")
        # Parse the HTML content
        strainer = SoupStrainer('a', class_='titlez')
        soup = BeautifulSoup(response.text, 'lxml', parse_only=strainer)

        # List to store search results
        search_results = []

        # Find all filtered span elements and their following sibling a elements
        for a_element in soup.find_all('a'):
            print(a_element)
            # Check if the text of the a element contains "↩"
            if '↩' not in a_element.get_text():
                logger.debug("extracting")
                # Extract href and text from the a element
                href = a_element.get('href')
                text = a_element.get_text(strip=True)

                # Use str.replace to extract id_val from the href
                id_start = href.find('unik=') + len('unik=')
                id_end = href.find('&', id_start) if '&' in href[id_start:] else None
                id_val = href[id_start:id_end]
                logger.debug(id_val)
                # split on the dot and get the first part
                # Extract lexical_category_val from the first span inside the a element
                first_span = a_element.find('span')
                logger.debug(first_span)
                lexical_category_val = first_span.get_text(strip=True).split(".")[0] if first_span else None
                logger.debug(f"lexical_category_val: '{lexical_category_val}'")
                # Create an instance of SearchResult and add it to the list
                search_result = SearchResult(href=href, text=text, id=id_val,
                                             lexical_category=lexical_category_val)
                pprint(search_result.model_dump())
                logger.info(f"lexical_category_qid: {search_result.lexical_category_qid}")
                search_results.append(search_result)
        return search_results

    def lookup_labels(self):
        wbi = WikibaseIntegrator(
            login=Login(user=config.user_name, password=config.bot_password)
        )
        for lid in self.lids:
            lexeme = wbi.lexeme.get(lid)
            lemma = lexeme.lemmas.get(language="sv")
            if not lemma:
                raise ValueError(f"no swedish lemma for this swedish lexeme")
            else:
                print(f"Working on '{lemma}'")
                # Adding the lookup to ordnet.dk
                search_url = f"{self.query_format_url}{quote(string=str(lemma))}"
                response = self.session.get(search_url)
                if response.status_code == 200:
                    # todo determine if we got a search result back
                    if self.is_search_result(response=response):
                        count = self.search_result_count(response=response)
                        print(count)
                        results = self.parse_search_results(response=response)
                        exit()
                    else:
                        # got entry
                        """search this path: .entry-content > table:nth-child(1) > tbody:nth-child(1) > tr:nth-child(1) > td:nth-child(2) > a:nth-child(1)
                        terrible, try /html/body/div[1]/div/div/div[1]/div/article/div/table/tbody/tr/td[2]/a"""
                        saob_lemma = self.get_saob_lemma(response=response)
                        if lemma != saob_lemma:
                            logger.warning(
                                f"lemmas do not match, got lemma {saob_lemma} from saob. "
                                f"These are often near matches, we skip them for now "
                                f"because we have not decided how to handle these yet. Skipping."
                            )
                            continue
                    # print(f"Ordnet.dk response for {lemma}:")
                    logger.info(search_url)
                    if self.is_single_hit_in_saob(response=response):
                        qid = self.find_lexical_category_qid(response=response)
                        if qid and qid == lexeme.lexical_category:
                            count = (
                                self.number_of_lexemes_with_identical_lemma_and_lexcat(
                                    lemma=lemma, lexcat=qid
                                )
                            )
                            if count == 1:
                                # check match url if idiom
                                match_url = self.get_match_url(response)
                                raise NotImplementedError("update to SAOB")
                                # logger.debug(match_url)
                                # if "mselect" not in match_url:
                                #     saob_article_id = self.get_saob_article_id(response)
                                #     print(saob_article_id)
                                #     saob_claim = ExternalID(
                                #         prop_nr="P9529", value=saob_article_id
                                #     )
                                #     lexeme.add_claims(claims=[saob_claim])
                                #     lexeme = self.remove_not_found_in_saob_if_present(
                                #         lexeme
                                #     )
                                #     self.enrich_wikidata(lexeme=lexeme)
                                #     # exit()
                                # else:
                                #     logger.info("Idiom detected")
                                #     mselect_start = match_url.find("mselect=")
                                #     if mselect_start != -1:
                                #         mselect_start += len("mselect=")
                                #         mselect_end = match_url.find("&", mselect_start)
                                #         if mselect_end == -1:
                                #             mselect_end = len(match_url)
                                #         saob_idiom_id = match_url[
                                #             mselect_start:mselect_end
                                #         ]
                                #         print(f"mselect value: {saob_idiom_id}")
                                #         saob_claim = ExternalID(
                                #             prop_nr="P9530", value=saob_idiom_id
                                #         )
                                #         lexeme.add_claims(claims=[saob_claim])
                                #         lexeme = (
                                #             self.remove_not_found_in_saob_if_present(
                                #                 lexeme
                                #             )
                                #         )
                                #         self.enrich_wikidata(lexeme=lexeme)
                                #     else:
                                #         raise ValueError(
                                #             "mselect value not found in the URL"
                                #         )
                            # sleep(1)
                            else:
                                print(
                                    "We don't support matching on lexemes where "
                                    "multiple exists with identical lemma and lexical category"
                                )
                        else:
                            print(
                                f"Lexical categories do not match, see {search_url} and {lexeme.get_entity_url()}, skipping"
                            )
                            input("press enter to continue")
                    else:
                        logger.info(
                            f"Not a single hit in SAOB, see {search_url}. We don't support these yet, skipping."
                        )
                else:
                    if response.status_code == 404:
                        print("Got 404 from saob, adding not found in statement")
                        # saob is a moving target so we add point in time to this
                        time = Time(prop_nr="P585", time="now", precision=11)
                        not_found_in_saob = Item(
                            prop_nr="P9660",
                            value="Q1186741",
                            qualifiers=Qualifiers().add(qualifier=time),
                        )
                        lexeme.add_claims(claims=[not_found_in_saob])
                        self.enrich_wikidata(lexeme=lexeme)
                        input("press enter to continue")
                    else:
                        raise FetchError(
                            f"Error getting data for {lemma}, see {search_url}"
                        )

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
