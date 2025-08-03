import logging
import re
from urllib.parse import quote

from bs4 import SoupStrainer, BeautifulSoup
from pydantic import BaseModel
from requests import Session
from wikibaseintegrator import WikibaseIntegrator
from wikibaseintegrator.datatypes import ExternalID, Time, Item
from wikibaseintegrator.entities import LexemeEntity
from wikibaseintegrator.models import Qualifiers
from wikibaseintegrator.wbi_helpers import execute_sparql_query

import config
from models.exceptions import FetchError, InformationMissing
from models.wikidata.foreign_id import ForeignID

logger = logging.getLogger(__name__)


class SaobLexeme(BaseModel):
    id: str # got from sparql
    lemma: str # got from sparql
    lexical_category: str # got from sparql
    wbi: WikibaseIntegrator
    session: Session
    saob_uid: str = ""  # hash used as part of the subentry_id e.g. U_F3169_181719
    foreign_id: ForeignID = None
    homographic_lexeme_count: int = 0

    class Config:
        arbitrary_types_allowed = True

    def url(self):
        return f"{config.wd_prefix}{self.id}"

    def generate_foreign_id(self):
        # fixme support main entry ids also
        if not self.saob_uid:
            return
            # self.foreign_id = ForeignID(property_=config.saob_main_entry_property, no_value=True)
        else:
            self.foreign_id = ForeignID(property_=config.saob_subentry_property, id=self.saob_subentry_id)

    def prepare_upload_to_wikidata(self, lexeme: LexemeEntity):
        """Upload to enrich the wonderfull Wikidata <3"""
        if not lexeme:
            raise InformationMissing()
        self.generate_foreign_id()
        # todo fix when main entry lemmas are supported
        # if self.foreign_id.no_value:
        #     # We did not find the lemma in SAOB
        #     # See https://www.saob.se/artikel/?pz=1&seek=%C3%A4rva
        #     print(f"Uploading no_value statement to {self.id}: {self.lemma}")
        #     time_object = WikidataTimeFormat(datetime=datetime.today())
        #     date_qualifier = Time(
        #         prop_nr="P585",
        #         value=time_object.day()
        #     )
        #     statement = ExternalID(
        #         prop_nr=,
        #         value=None,
        #         snak_type="novalue",
        #         qualifiers=date_qualifier
        #     )
        #     item = ItemEntity(
        #         data=[statement],
        #         item_id=self.id
        #     )
        #     # debug WBI error
        #     # print(item.get_json_representation())
        # else:

        # We found the lemma in SAOB
        print(f"Uploading {self.saob_subentry_id} to {self.id}: {self.lemma}")
        statement = ExternalID(
            prop_nr=self.foreign_id.property_id,
            value=self.foreign_id.id,
        )
        lexeme.add_claims(claims=[statement])
        self.enrich_wikidata(lexeme=lexeme)
        # debug WBI error
        # print(item.get_json_representation())
    # @staticmethod
    # def is_single_hit_in_saob(response) -> bool:
    #     logger.debug("is_single_hit_in_saob: running")
    #     # fixme update to saob
    #     raise NotImplementedError()
    #
    #     only_div_tags = SoupStrainer("div")
    #     soup = BeautifulSoup(response.text, "lxml", parse_only=only_div_tags)
    #     # Select the first div with class 'diskret'
    #     first_diskret_div = soup.find("div", class_="diskret")
    #
    #     # Get the text content inside the first div
    #     if first_diskret_div:
    #         text_inside_first_div = first_diskret_div.get_text()
    #         logger.debug(text_inside_first_div)
    #         if text_inside_first_div.strip() == "(1)":
    #             logger.debug("Content of the div is '(1)'")
    #             # todo add the id of this entry to wikidata
    #             return True
    #         else:
    #             logger.debug("Content of the div is not '(1)'")
    #             return False
    #     else:
    #         raise ValueError("No div with class 'diskret' found.")

    # @staticmethod
    # def get_match_url(response):
    #     logger.debug("get_match_url: running")
    #     raise NotImplementedError("update to SAOB")
    #
    #     only_a_tags = SoupStrainer("a")
    #     soup = BeautifulSoup(response.text, "lxml", parse_only=only_a_tags)
    #     # Find the first anchor element with class 'searchMatch'
    #     return soup.find("a", class_="searchMatch")

    # @staticmethod
    # def get_saob_article_id(response) -> str:
    #     logger.debug("get_saob_article_id: running")
    #
    #     raise NotImplementedError("update to SAOB")
    #     from bs4 import SoupStrainer
    #
    #     only_a_tags = SoupStrainer("a")
    #     soup = BeautifulSoup(response.text, "lxml", parse_only=only_a_tags)
    #     # Find the first anchor element with class 'searchMatch'
    #     # Find the anchor element with class 'fejlrapport'
    #     anchor = soup.find("a", class_="fejlrapport")
    #
    #     # Extract the value of the href attribute
    #     if anchor:
    #         href_value = anchor.get("href")
    #         logger.debug(href_value)
    #         return href_value.split("(")[1].rstrip(")")
    #     else:
    #         raise ValueError("Anchor element not found.")

    def find_homographs(self) -> None:
        """number_of_lexemes_with_identical_lemma_and_lexcat"""
        query = f"""
            SELECT (COUNT(?lexeme) as ?count) WHERE {{
                ?lexeme dct:language wd:Q9035;
                        wikibase:lemma "{self.lemma}"@da;
                        wikibase:lexicalCategory wd:{self.lexical_category}.
            }}
        """
        data = execute_sparql_query(query)
        self.homographic_lexeme_count = int(data["results"]["bindings"][0]["count"]["value"])
        logger.info(f"Found {self.homographic_lexeme_count} lexemes with the same lemma and category in WD")

    # @staticmethod
    # def get_saob_lemma(response) -> str:
    #     logger.debug("get_saob_lemma: running")
    #     return response.url

    @property
    def is_proper_noun(self):
        return bool(self.lexical_category == "Q147276")

    @property
    def saob_url(self):
        return f"{config.query_format_url}{quote(self.lemma)}#{self.saob_uid}"

    def get_saob_uid(self, response) -> None:
        """This is called 'ankare' in the js and look like this U_F3169_181719"""
        logger.debug("get_saob_uid: running")

        match = re.search(r'var ankare = "([^"]+)"', response.text)
        if match:
            self.saob_uid = str(match.group(1))
            logger.info(f"Hittade subentry_id '{self.saob_subentry_id}', se {self.saob_url}")
            # input("press enter to continue")
        else:
            logger.info("Hittade inget subentry_id.")

    @staticmethod
    def enrich_wikidata(
        lexeme: LexemeEntity,
    ):
        logger.debug("enrich_wikidata: running")

        # print(lexeme.get_entity_url())
        # pprint(self.item.get_json())
        if config.press_enter_to_continue:
            input("press enter to upload")
        lexeme.write(
            summary="Adding SAOB identifier with [[Wikidata:Tools/LexSAOB|LexSAOB]]"
        )
        print(f"Upload done to {lexeme.get_entity_url()}")
        # if config.press_enter_to_continue:
        #     input("press enter to continue")

    # def remove_not_found_in_saob_if_present(self, lexeme):
    #     logger.debug("remove_not_found_in_saob_if_present: running")
    #
    #     try:
    #         not_found_in = lexeme.claims.get(property=self.property_to_work_on)
    #         for claim in not_found_in:
    #             logger.debug(claim.mainsnak.datavalue)
    #             # exit()
    #             if claim.mainsnak.datavalue["value"]["id"] == self.dictionary_item:
    #                 claim.remove()
    #                 print("Removed not found in -> SAOB statement")
    #                 input("press enter to continue")
    #         # This should cause the claim to be removed
    #     except KeyError:
    #         pass
    #     return lexeme

    # @staticmethod
    # def search_result_count(response) -> int:
    #     # Define the SoupStrainer to filter div tags with the specified class
    #     strainer = SoupStrainer('div', class_='alert alert-block')
    #
    #     # Parse the HTML content with the strainer
    #     soup = BeautifulSoup(response.text, 'lxml', parse_only=strainer)
    #
    #     # Extract the text content
    #     if soup.div:
    #         text_content = soup.div.get_text(strip=True)
    #
    #         # Split the text and extract the first number
    #         numbers = [int(s) for s in text_content.split() if s.isdigit()]
    #
    #         if numbers:
    #             first_number = numbers[0]
    #             # print("First number:", first_number)
    #             return first_number
    #         else:
    #             raise ValueError("No numbers found in the text.")
    #     else:
    #         raise ValueError("Div not found.")

    @staticmethod
    def is_search_result(response):
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

    # @staticmethod
    # def parse_search_results(response) -> List[SearchResult]:
    #     """ignore ↩ which is a redirect we dont care about
    #
    #     the html looks like this
    #     <a class="titlez" href="/artikel/?unik=T_0915-0036.3pwB&amp;pz=3">test &nbsp;  <span class="caset">sbst. 2</span></a><br>
    #     <a class="titlez" href="/artikel/?unik=T_0915-0037.Ut0B&amp;pz=3">test &nbsp;  <span class="caset">sbst. 3</span></a><br>"""
    #     logger.debug("parsing search results")
    #     # Parse the HTML content
    #     strainer = SoupStrainer('a', class_='titlez')
    #     soup = BeautifulSoup(response.text, 'lxml', parse_only=strainer)
    #
    #     # List to store search results
    #     search_results = []
    #
    #     # Find all filtered span elements and their following sibling a elements
    #     for a_element in soup.find_all('a'):
    #         print(a_element)
    #         # Check if the text of the a element contains "↩"
    #         if '↩' not in a_element.get_text():
    #             logger.debug("extracting")
    #             # Extract href and text from the a element
    #             href = a_element.get('href')
    #             text = a_element.get_text(strip=True)
    #
    #             # Use str.replace to extract id_val from the href
    #             id_start = href.find('unik=') + len('unik=')
    #             id_end = href.find('&', id_start) if '&' in href[id_start:] else None
    #             id_val = href[id_start:id_end]
    #             logger.debug(id_val)
    #             # split on the dot and get the first part
    #             # Extract lexical_category_val from the first span inside the a element
    #             first_span = a_element.find('span')
    #             logger.debug(first_span)
    #             lexical_category_val = first_span.get_text(strip=True).split(".")[0] if first_span else None
    #             logger.debug(f"lexical_category_val: '{lexical_category_val}'")
    #             # Create an instance of SearchResult and add it to the list
    #             search_result = SearchResult(href=href, text=text, id=id_val,
    #                                          lexical_category=lexical_category_val)
    #             pprint(search_result.model_dump())
    #             logger.info(f"lexical_category_qid: {search_result.lexical_category_qid}")
    #             search_results.append(search_result)
    #     return search_results

    @property
    def saob_subentry_id(self):
        return f"{self.lemma}#{self.saob_uid}"

    def store_processed_lexeme_id(self, filepath: str = config.processed_lexeme_ids) -> None:
        """Append matched lexeme ID and lemma to a file."""
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(f"{self.id}\t{self.lemma}\t{self.saob_subentry_id}\n")
            logger.info(f"Stored matched lexeme: {self.id} ({self.lemma})")
        except Exception as e:
            logger.error(f"Failed to write lexeme ID to file: {e}")

    def already_processed(self, filepath: str = config.processed_lexeme_ids) -> bool:
        """Check if the given lexeme ID exists in the file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith(self.id + "\t"):
                        return True
            return False
        except FileNotFoundError:
            logger.warning(f"File not found: {filepath}")
            return False
        except Exception as e:
            logger.error(f"Error reading file {filepath}: {e}")
            return False

    def match_and_improve(self):
        if self.already_processed():
            print("Skipping already processed lexeme")
            return
        self.find_homographs()
        if self.homographic_lexeme_count > 1:
            print(f"{self.homographic_lexeme_count} homographs exists for, skipping")
        elif self.is_proper_noun and len(self.lemma) <= 12:
            print(f"{self.id} is a proper noun and the lemma is not longer than 12 chars, skipping to avoid bad matches")
        else:
            print(f"Working on '{self.lemma}'")
            search_url = f"{config.query_format_url}{quote(string=str(self.lemma))}"
            response = self.session.get(search_url)
            logger.debug("Fetching lexeme data from wikidata")
            lexeme = self.wbi.lexeme.get(self.id)
            print("Looking up in SAOB")
            if response.status_code == 200:
                logger.debug("got 200 from SAOB")
                if self.is_search_result(response=response):
                    logger.info("Skipping unsupported search result page")
                    # count = self.search_result_count(response=response)
                    # print(count)
                    # raise NotImplementedError("parsing search results is not implemented yet")
                    # results = self.parse_search_results(response=response)
                    # exit()
                else:
                    # got entry
                    self.get_saob_uid(response=response)
                    if self.saob_uid:
                        if self.is_proper_noun:
                            print(f"{self.id} {self.lemma} is proper noun, see {self.saob_url}")
                            input("press enter to continue")
                        self.prepare_upload_to_wikidata(lexeme=lexeme)
                    else:
                        logger.info("finding saob_lemma is not implemented yet, skipping")
                        # raise NotImplementedError("finding saob_lemma is not implemented yet")
                        # saob_lemma = self.get_saob_lemma(response=response)
                        # if self.lemma != saob_lemma:
                        #     logger.warning(
                        #         f"lemmas do not match, got lemma {saob_lemma} from saob. "
                        #         f"These are often near matches, we skip them for now "
                        #         f"because we have not decided how to handle these yet. Skipping."
                        #     )
                        #     return
                # print(f"Ordnet.dk response for {lemma}:")
                # logger.info(search_url)
                # # todo adapt to SAOB
                # if self.is_single_hit_in_saob(response=response):
                #     qid = self.find_lexical_category_qid(response=response)
                #     if qid and qid == lexeme.lexical_category:
                #         count = (
                #             self.number_of_lexemes_with_identical_lemma_and_lexcat(
                #                 lemma=self.lemma, lexcat=qid
                #             )
                #         )
                #         if count == 1:
                #             # check match url if idiom
                #             #match_url = self.get_match_url(response)
                #             raise NotImplementedError("update to SAOB")
                #             # logger.debug(match_url)
                #             # if "mselect" not in match_url:
                #             #     saob_article_id = self.get_saob_article_id(response)
                #             #     print(saob_article_id)
                #             #     saob_claim = ExternalID(
                #             #         prop_nr="P9529", value=saob_article_id
                #             #     )
                #             #     lexeme.add_claims(claims=[saob_claim])
                #             #     lexeme = self.remove_not_found_in_saob_if_present(
                #             #         lexeme
                #             #     )
                #             #     self.enrich_wikidata(lexeme=lexeme)
                #             #     # exit()
                #             # else:
                #             #     logger.info("Idiom detected")
                #             #     mselect_start = match_url.find("mselect=")
                #             #     if mselect_start != -1:
                #             #         mselect_start += len("mselect=")
                #             #         mselect_end = match_url.find("&", mselect_start)
                #             #         if mselect_end == -1:
                #             #             mselect_end = len(match_url)
                #             #         saob_idiom_id = match_url[
                #             #             mselect_start:mselect_end
                #             #         ]
                #             #         print(f"mselect value: {saob_idiom_id}")
                #             #         saob_claim = ExternalID(
                #             #             prop_nr="P9530", value=saob_idiom_id
                #             #         )
                #             #         lexeme.add_claims(claims=[saob_claim])
                #             #         lexeme = (
                #             #             self.remove_not_found_in_saob_if_present(
                #             #                 lexeme
                #             #             )
                #             #         )
                #             #         self.enrich_wikidata(lexeme=lexeme)
                #             #     else:
                #             #         raise ValueError(
                #             #             "mselect value not found in the URL"
                #             #         )
                #         # sleep(1)
                #         else:
                #             print(
                #                 "We don't support matching on lexemes where "
                #                 "multiple exists with identical lemma and lexical category"
                #             )
                #     else:
                #         print(
                #             f"Lexical categories do not match, see {search_url} and {lexeme.get_entity_url()}, skipping"
                #         )
                #         input("press enter to continue")
                # else:
                #     logger.info(
                #         f"Not a single hit in SAOB, see {search_url}. We don't support these yet, skipping."
                #     )
            else:
                if response.status_code == 404:
                    print("Got 404 from saob, adding not found in statement")
                    print("debug exit")
                    exit(0)
                    # saob is a moving target so we add point in time to this
                    time = Time(prop_nr="P585", time="now", precision=11)
                    not_found_in_saob = Item(
                        prop_nr="P9660",
                        value="Q1186741",
                        qualifiers=Qualifiers().add(qualifier=time),
                    )
                    lexeme.add_claims(claims=[not_found_in_saob])
                    self.enrich_wikidata(lexeme=lexeme)
                else:
                    raise FetchError(
                        f"Error getting data for {self.lemma}, see {search_url}"
                    )
            self.store_processed_lexeme_id()
