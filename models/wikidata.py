import logging
from enum import Enum
from typing import List

from wikibaseintegrator import wbi_core, wbi_datatype

# This config sets the URL for the Wikibase and tool.
from wikibaseintegrator.wbi_functions import execute_sparql_query

import config
from modules import wdqs


class WikimediaLanguageCode(Enum):
    DANISH = "da"
    SWEDISH = "sv"
    BOKMÅL = "nb"
    ENGLISH = "en"
    FRENCH = "fr"
    RUSSIAN = "ru"
    ESTONIAN = "et"
    MALAYALAM = "ml"
    LATIN = "la"
    HEBREW = "he"
    BASQUE = "eu"
    GERMAN = "de"
    BENGALI = "bn"
    CZECH = "cs"


class WikimediaLanguageQID(Enum):
    DANISH = "Q9035"
    SWEDISH = "Q9027"
    BOKMÅL = "Q25167"
    ENGLISH = "Q1860"
    FRENCH = "Q150"
    RUSSIAN = "Q7737"
    ESTONIAN = "Q9072"
    MALAYALAM = "Q36236"
    LATIN = "Q397"
    HEBREW = "Q9288"
    BASQUE = "Q8752"
    GERMAN = "Q188"
    BENGALI = "Q9610"
    CZECH = "Q9056"


class WikidataNamespaceLetters(Enum):
    PROPERTY = "P"
    ITEM = "Q"
    LEXEME = "L"


class WikidataNamespaceLetters(Enum):
    PROPERTY = "P"
    ITEM = "Q"
    LEXEME = "L"


class EntityID:
    letter: WikidataNamespaceLetters
    number: int

    def __init__(self,
                 entity_id: str = None):
        if entity_id is not None:
            if len(entity_id) > 1:
                self.letter = WikidataNamespaceLetters(entity_id[0])
                self.number = int(entity_id[1:])
            else:
                raise Exception("Entity ID was too short.")
        else:
            raise Exception("Entity ID was None")

    def to_string(self):
        return f"{self.letter.value}{self.number}"


class ForeignID:
    id: str
    no_value: bool
    property: str  # This is the property with type ExternalId
    source_item_id: str  # This is the Q-item for the source

    def __init__(self,
                 id: str = None,
                 property: str = None,
                 source_item_id: str = None,
                 no_value: bool = False):
        self.id = id
        if property is None:
            raise Exception("Property is mandatory.")
        self.property = EntityID(property).to_string()
        if source_item_id is not None:
            self.source_item_id = EntityID(source_item_id).to_string()
        self.no_value = no_value

class Lexeme:
    id: str
    lemma: str
    lexical_category: str

    def __init__(self,
                 id: str = None,
                 lemma: str = None,
                 lexical_category: str = None):
        self.id = EntityID(id).to_string()
        self.lemma = lemma
        self.lexical_category = lexical_category

    def url(self):
        return f"{config.wd_prefix}{self.id}"

    def upload_foreign_id_to_wikidata(self,
                                      foreign_id: ForeignID = None):
        """Upload to enrich the wonderfull Wikidata <3"""
        logger = logging.getLogger(__name__)
        if foreign_id is None:
            raise Exception("Foreign id was None")
        elif foreign_id.no_value:
            # We did not find the lemma in SAOB
            # See https://www.saob.se/artikel/?pz=1&seek=%C3%A4rva
            # Skip unsupported lemmas
            supported_by_saob = "abcdefghijklmnopqrstu"
            if self.lemma[:1] not in supported_by_saob:
                logger.debug("Skip adding no-value to this lemma because "
                             "SAOB only published lemma from a-u.")
            else:
                print(f"Uploading no_value statement to {self.id}: {self.lemma}")
                statement = wbi_datatype.ExternalID(
                    prop_nr=foreign_id.property,
                    value=None,
                    snak_type="novalue",
                )
                item = wbi_core.ItemEngine(
                    data=[statement],
                    item_id=self.id
                )
                # debug WBI error
                # print(item.get_json_representation())
                result = item.write(
                    config.login_instance,
                    edit_summary=f"Added foreign identifier with [[{config.tool_url}]]"
                )
                logger.debug(f"result from WBI:{result}")
                print(self.url())
                #exit(0)
        else:
            # We found the lemma in SAOB
            print(f"Uploading {foreign_id.id} to {self.id}: {self.lemma}")
            statement = wbi_datatype.ExternalID(
                prop_nr=foreign_id.property,
                value=foreign_id.id,
            )
            described_by_source = wbi_datatype.ItemID(
                prop_nr="P1343",  # stated in
                value=foreign_id.source_item_id
            )
            item = wbi_core.ItemEngine(
                data=[statement,
                      described_by_source],
                item_id=self.id
            )
            # debug WBI error
            # print(item.get_json_representation())
            result = item.write(
                config.login_instance,
                edit_summary=f"Added foreign identifier with [[{config.tool_url}]]"
            )
            logger.debug(f"result from WBI:{result}")
            print(self.url())
            # exit(0)

class Form:
    pass


class Sense:
    pass


class LexemeLanguage:
    lexemes: List[Lexeme] = []
    language_code: WikimediaLanguageCode
    language_qid: WikimediaLanguageQID
    senses_with_P5137_per_lexeme: float
    senses_with_P5137: int
    forms: int
    forms_with_an_example: int
    forms_without_an_example: List[Form]
    lexemes_count: int

    def __init__(self, language_code: str):
        self.language_code = WikimediaLanguageCode(language_code)
        self.language_qid = WikimediaLanguageQID[self.language_code.name]

    def __str__(self):
        return (f"{self.language_code.name} has "
                f"{self.senses_with_P5137} senses with linked "
                f"QID in total on {self.lexemes_count} lexemes "
                f"which is {self.senses_with_P5137_per_lexeme} "
                f"per lexeme.")

    def fetch_forms_missing_an_example(self):
        logger = logging.getLogger(__name__)
        results = execute_sparql_query(f'''
            #title:Forms that have no example demonstrating them
            select ?form ?lemma
            WHERE {{
              ?lexemeId dct:language wd:{self.language_qid.value};
                        wikibase:lemma ?lemma;
                        ontolex:lexicalForm ?form.
              MINUS {{
              ?lexemeId p:P5831 ?statement.
              ?statement ps:P5831 ?example;
                         pq:P6072 [];
                         pq:P5830 ?form_with_example.
              }}
            }}
            limit 1000''')
        self.forms_without_an_example = []
        logger.info("Got the data")
        for entry in results:
            logging.debug(f"lexeme_json:{entry}")
            f = Form.parse_from_wdqs_json(entry)
            self.forms_without_an_example.append(f)
        logger.info(f"Got {len(self.forms_without_an_example)} "
                     f"forms from WDQS for language {self.language_code.name}")

    def fetch_lexemes(self):
        # TODO port to use the Lexeme class instead of heavy dataframes which we don't need
        raise Exception("This is deprecated.")
        results = execute_sparql_query(f'''
        SELECT DISTINCT
        ?entity_lid ?form ?word (?categoryLabel as ?category) (?grammatical_featureLabel as ?feature) ?sense ?gloss
        WHERE {{
          ?entity_lid a ontolex:LexicalEntry; dct:language wd:{self.language_qid.value}.
          VALUES ?excluded {{
            # exclude affixes and interfix
            wd:Q62155 # affix
            wd:Q134830 # prefix
            wd:Q102047 # suffix
            wd:Q1153504 # interfix
          }}
          MINUS {{?entity_lid wdt:P31 ?excluded.}}
          ?entity_lid wikibase:lexicalCategory ?category.

          # We want only lexemes with both forms and at least one sense
          ?entity_lid ontolex:lexicalForm ?form.
          ?entity_lid ontolex:sense ?sense.

          # Exclude lexemes without a linked QID from at least one sense
          ?sense wdt:P5137 [].
          ?sense skos:definition ?gloss.
          # Get only the swedish gloss, exclude otherwise
          FILTER(LANG(?gloss) = "{self.language_code.value}")

          # This remove all lexemes with at least one example which is not
          # ideal
          MINUS {{?entity_lid wdt:P5831 ?example.}}
          ?form wikibase:grammaticalFeature ?grammatical_feature.
          # We extract the word of the form
          ?form ontolex:representation ?word.
          SERVICE wikibase:label
          {{ bd:serviceParam wikibase:language "{self.language_code.value},en". }}
        }}
        limit {config.sparql_results_size}
        offset {config.sparql_offset}
        ''')
        self.lexemes = []
        for lexeme_json in results:
            logging.debug(f"lexeme_json:{lexeme_json}")
            l = Lexeme.parse_wdqs_json(lexeme_json)
            self.lexemes.append(l)
        logging.info(f"Got {len(self.lexemes)} lexemes from WDQS for language {self.language_code.name}")

    def count_number_of_lexemes(self):
        """Returns an int"""
        logger = logging.getLogger(__name__)
        result = (execute_sparql_query(f'''
        SELECT
        (COUNT(?l) as ?count)
        WHERE {{
          ?l dct:language wd:{self.language_qid.value}.
        }}'''))
        logger.debug(f"result:{result}")
        count: int = wdqs.extract_count(result)
        logging.debug(f"count:{count}")
        return count

    def count_number_of_senses_with_p5137(self):
        """Returns an int"""
        logger = logging.getLogger(__name__)
        result = (execute_sparql_query(f'''
        SELECT
        (COUNT(?sense) as ?count)
        WHERE {{
          ?l dct:language wd:{self.language_qid.value}.
          ?l ontolex:sense ?sense.
          ?sense skos:definition ?gloss.
          # Exclude lexemes without a linked QID from at least one sense
          ?sense wdt:P5137 [].
        }}'''))
        logger.debug(f"result:{result}")
        count: int = wdqs.extract_count(result)
        logging.debug(f"count:{count}")
        return count

    def count_number_of_forms_without_an_example(self):
        """Returns an int"""
        # TODO fix this to count all senses in a given language
        result = (execute_sparql_query(f'''
        SELECT
        (COUNT(?form) as ?count)
        WHERE {{
          ?l dct:language wd:{self.language_qid.value}.
          ?l ontolex:lexicalForm ?form.
          ?l ontolex:sense ?sense.
          # exclude lexemes that already have at least one example
          MINUS {{?l wdt:P5831 ?example.}}
          # Exclude lexemes without a linked QID from at least one sense
          ?sense wdt:P5137 [].
        }}'''))
        count: int = wdqs.extract_count(result)
        logging.debug(f"count:{count}")
        self.forms_without_an_example = count

    def count_number_of_forms_with_examples(self):
        pass

    def count_number_of_forms(self):
        pass

    def calculate_statistics(self):
        self.lexemes_count: int = self.count_number_of_lexemes()
        self.senses_with_P5137: int = self.count_number_of_senses_with_p5137()
        self.calculate_senses_with_p5137_per_lexeme()

    def calculate_senses_with_p5137_per_lexeme(self):
        self.senses_with_P5137_per_lexeme = round(self.senses_with_P5137 / self.lexemes_count, 3)

    def fetch_all_lexemes_without_saob_id(self):
        """download all swedish lexemes via sparql (~23000 as of 2021-04-05)"""
        # dictionary with word as key and list in the value
        # list[0] = lid
        # list[1] = category Qid
        print("Fetching all lexemes")
        lexemes_data = {}
        lexeme_lemma_list = []
        for i in range(0, 30000, 10000):
            print(i)
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
                  MINUS {{
                    # Exclude truthy no value statements
                    ?lexemeId a wdno:P8478.                  
                  }}
                }}
        limit 10000
        offset {i}
            """)
            if len(results) == 0:
                print("No lexeme found")
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
                    self.lexemes.append(Lexeme(
                        id=lid,
                        lemma=lemma,
                        lexical_category=lexical_category
                    ))
        print(f"{len(self.lexemes)} fetched")

    def lemma_list(self):
        lemmas = []
        for lexeme in self.lexemes:
            lemmas.append(lexeme.lemma)
        return lemmas

    def data_dictionary_with_lemma_as_key(self):
        data = {}
        for lexeme in self.lexemes:
            data[lexeme.lemma] = lexeme
        return data
