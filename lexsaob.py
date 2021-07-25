#!/usr/bin/env python3
# Licensed under GPLv3+ i.e. GPL version 3 or later.
import logging
from csv import reader
from typing import List, Dict
from urllib.parse import urlparse, parse_qsl

from wikibaseintegrator import wbi_core, wbi_login

import config
from models import wikidata_lexeme, saob_entry

# Constants
wd_prefix = "http://www.wikidata.org/entity/"
count_only = False

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

def upload_to_wikidata(lexeme: wikidata_lexeme.Lexeme = None,
                       saob_entry: saob_entry.SAOBEntry = None):
    """Upload to enrich the wonderfull Wikidata <3"""
    if lexeme is None or saob_entry is None:
        raise ValueError("Did not get the arguments needed")
    print(f"Uploading id to {lexeme.id}: {lexeme.lemma}")
    # TODO if numbered
    # - fetch lexeme using wbi
    # - present to user
    # - ask user which if one matches
    print(f"Adding {saob_entry.id}")
    saob_statement = wbi_core.ExternalID(
        prop_nr="P8478",
        value=saob_entry.id,
    )
    described_by_source = wbi_core.ItemID(
        prop_nr="P1343",
        value="Q1935308"
    )
    item = wbi_core.ItemEngine(
        data=[saob_statement,
              described_by_source],
        # append_value="P8478",
        item_id=lexeme.id
    )
    # debug WBI error
    # print(item.get_json_representation())
    result = item.write(
        login_instance,
        edit_summary="Added SAOB identifier with [[Wikidata:Tools/LexSAOB]]"
    )
    # if config.debug_json:
    # logging.debug(f"result from WBI:{result}")
    print(lexeme.url())
    # exit(0)


def check_matching_category(lexeme: wikidata_lexeme.Lexeme = None,
                            saob_entry: saob_entry.SAOBEntry = None) -> bool:
    logger = logging.getLogger(__name__)
    if lexeme is None or saob_entry is None:
        raise ValueError("Did not get the arguments needed")
    # TODO find out what the number means and how it affects the matching
    logger.debug(f"SAOB number: {saob_entry.number}")
    # if not count_only:
    #     logger.info(f"found match: category: {saob_entry.lexical_category} id: {saob_entry.id}")
    # check if categories match
    category = None
    if saob_entry.lexical_category == "" or saob_entry.lexical_category is None:
        if not count_only:
            logging.info("No category found")
    elif "verb" in saob_entry.lexical_category:
        category = "Q24905"
    elif "subst" in saob_entry.lexical_category:
        if "-" in saob_entry.lemma:
            # handle affixes like -fil also being marked as subst in SAOB
            category = "Q62155"
        else:
            category = "Q1084"
    elif "adj" in saob_entry.lexical_category:
        category = "Q34698"
    elif "adv" in saob_entry.lexical_category:
        category = "Q380057"
    elif "konj" in saob_entry.lexical_category:
        category = "Q36484"
    elif "interj" in saob_entry.lexical_category:
        category = "Q83034"
    elif "prep" in saob_entry.lexical_category:
        category = "Q4833830"
    elif "räkn" in saob_entry.lexical_category:
        category = "Q63116"
    elif "artikel" in saob_entry.lexical_category:
        category = "Q103184"
    elif "pron" in saob_entry.lexical_category:
        category = "Q36224"
    elif (
        saob_entry.lexical_category == "prefix" or
        saob_entry.lexical_category == "suffix" or
        saob_entry.lexical_category == "affix"
    ):
        category = "Q62155"
    elif (
        # this covers all special cases like this one: https://svenska.se/saob/?id=O_0283-0242.Qqdq&pz=5
        "(" in saob_entry.lexical_category or
        "ssgled" in saob_entry.lexical_category
    ):
        # ignore silently
        return False
    else:
        if not count_only:
            logging.error(f"Did not recognize category "
                          f"{saob_entry.lexical_category} on "
                          f"{saob_entry.url()}, skipping")
            return False
    if category is not None:
        if category == lexeme.lexical_category:
            return True
        else:
            if not count_only:
                logging.info("Categories did not match, skipping")
            return False


if not count_only:
    print("Logging in with Wikibase Integrator")
    login_instance = wbi_login.Login(
        user=config.username, pwd=config.password
    )


def fetch_all_lexemes_without_saob_id():
    """download all swedish lexemes via sparql (~23000 as of 2021-04-05)"""
    #dictionary with word as key and list in the value
    #list[0] = lid
    #list[1] = category Qid
    print("Fetching all lexemes")
    lexemes_data = {}
    lexeme_lemma_list = []
    for i in range(0,30000,10000):
        print(i)
        results = wbi_core.ItemEngine.execute_sparql_query(f"""
                select ?lexemeId ?lemma ?category
            WHERE {{
              #hint:Query hint:optimizer "None".
              ?lexemeId dct:language wd:Q9027;
                        wikibase:lemma ?lemma;
                        wikibase:lexicalCategory ?category.
              MINUS{{
                ?lexemeId wdt:P8478 [].
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
                #print(result)
                #*************************
                # Handle result and upload
                #*************************
                lemma = result["lemma"]["value"]
                lid = result["lexemeId"]["value"].replace(wd_prefix, "")
                lexical_category = result["category"]["value"].replace(wd_prefix, "")
                lexeme = wikidata_lexeme.Lexeme(
                    id=lid,
                    lemma=lemma,
                    lexical_category=lexical_category
                )
                # Populate the dictionary with lexeme objects
                lexemes_data[lemma] = lexeme
                # Add lemma to list (used for optimization)
                lexeme_lemma_list.append(lemma)
    lexemes_count = len(lexeme_lemma_list)
    print(f"{lexemes_count} fetched")
    # exit(0)
    return lexeme_lemma_list, lexemes_data


def load_saob_into_memory():
    # load all saab words into a list that can be searched
    # load all saab ids into a list we can lookup in using the index.
    # the two lists above have the same index.
    # load all saob lines into a dictionary with count as key and list in the value
    #list[0] = saob_category
    #list[1] = number
    #list[2] = id
    #list[3] = word
    print("Loading SAOB into memory")
    saob_lemma_list = []
    saob_data = {}
    # open file in read mode
    with open('saob_2021-01-06.csv', 'r') as read_obj:
        # pass the file object to reader() to get the reader object
        csv_reader = reader(read_obj)
        count = 0
        # Iterate over each row in the csv using reader object
        for row in csv_reader:
            # row variable is a list that represents a row in csv
            #row0 is null
            word = row[1]
            saob_category = row[2]
            if row[3] == '':
                saob_number = 0
            else:
                saob_number = int(row[3])
            url = urlparse(row[4])
            # print(url.query)
            saob_id = dict(parse_qsl(url.query))["id"]
            # Create object
            entry = saob_entry.SAOBEntry(
                id=saob_id,
                lexical_category=saob_category,
                number=saob_number,
                lemma=word
            )
            saob_data[count] = entry #[saob_category, saob_number, saob_id, word]
            saob_lemma_list.append(word)
            count += 1
    print(f"loaded {count} saob lines into dictionary with length {len(saob_data)}")
    print(f"loaded {count} saob lines into list with length {len(saob_lemma_list)}")
    # exit(0)
    return saob_lemma_list, saob_data


def process_lexemes(lexeme_lemma_list: List = None,
                    lexemes_data: Dict = None,
                    saob_lemma_list: List = None,
                    saob_data: Dict = None):
    if (
        lexeme_lemma_list is None or
        lexemes_data is None or
        saob_lemma_list is None or
        saob_data is None
    ):
        logger.exception("Did not get what we need")
    lexemes_count = len(lexeme_lemma_list)
    # go through all lexemes missing SAOB identifier
    match_count = 0
    processed_count = 0
    skipped_multiple_matches = 0
    if count_only:
        print("Counting all matches that can be uploaded")
    for lexeme in lexeme_lemma_list:
        if processed_count > 0 and processed_count % 1000 == 0:
            print(f"Processed {processed_count} lexemes out of "
                  f"{lexemes_count} ({round(processed_count * 100 / lexemes_count)}%)")
        lexeme: wikidata_lexeme.Lexeme = lexemes_data[lexeme]
        if not count_only:
            logging.info(f"Working on {lexeme.id}: {lexeme.lemma} {lexeme.lexical_category}")
        value_count = 0
        matching_saob_indexes = []
        if lexeme.lemma in saob_lemma_list:
            # Count number of hits
            for count, lemma in enumerate(saob_lemma_list):
                if lemma == lexeme.lemma:
                    # print(count, value)
                    matching_saob_indexes.append(count)
                    value_count += 1
            if value_count > 1:
                if not count_only:
                    logger.debug(f"Found more than 1 matching lemma = complex")
                    adj_count = 0
                    subst_count = 0
                    verb_count = 0
                    adjective_regex = "adj"
                    for index in matching_saob_indexes:
                        entry = saob_data[index]
                        if "subst" in entry.lexical_category:
                            logging.debug(f"Detected noun: {entry.lexical_category}")
                            subst_count += 1
                        if "verb" in entry.lexical_category:
                            logging.debug(f"Detected verb: {entry.lexical_category}")
                            verb_count += 1
                        if "adj" in entry.lexical_category:
                            logging.debug(f"Detected adjective: {entry.lexical_category}")
                            adj_count += 1
                    for index in matching_saob_indexes:
                        entry = saob_data[index]
                        logging.debug(f"index {index} lemma: {entry.lemma} {entry.lexical_category} "
                              f"number {entry.number}, see {entry.url()}")
                        result: bool = check_matching_category(lexeme=lexeme,
                                                               saob_entry=entry)
                        if result:
                            logging.info("Categories match")
                            match_count += 1
                            if not count_only:
                                if entry.lexical_category == "subst":
                                    if subst_count > 1:
                                        logging.info("More that one noun found. Skipping")
                                        skipped_multiple_matches += 1
                                        continue
                                if entry.lexical_category == "verb":
                                    if verb_count > 1:
                                        logging.info("More that one verb found. Skipping")
                                        skipped_multiple_matches += 1
                                        continue
                                if entry.lexical_category == "adj":
                                    if adj_count > 1:
                                        logging.info("More that one adj found. Skipping")
                                        skipped_multiple_matches += 1
                                        continue
                                # TODO scrape entry definitions from saob and let the user decide
                                # whether any match the senses of the lexeme if any
                                upload_to_wikidata(lexeme=lexeme,
                                                   saob_entry=entry)
            elif value_count == 1:
                # Only 1 search result in the saob wordlist so pick it
                entry = saob_data[matching_saob_indexes[0]]
                logger.debug(f"Only 1 matching lemma, see {entry.url()}")
                result = check_matching_category(lexeme=lexeme,
                                                 saob_entry=entry)
                if result:
                    match_count += 1
                    if not count_only:
                        upload_to_wikidata(lexeme=lexeme,
                                           saob_entry=entry)
        else:
            if not count_only:
                logging.debug(f"{lexeme.lemma} not found in SAOB wordlist")
        processed_count += 1
    print(f"Processed {processed_count} lexemes. "
          f"Found {match_count} matches "
          f"out of which {skipped_multiple_matches} "
          f"was skipped because they had multiple entries "
          f"with the same lexical category.")


def main():
    lexemes_list, lexemes_data = fetch_all_lexemes_without_saob_id()
    saob_list, saob_data = load_saob_into_memory()
    process_lexemes(lexeme_lemma_list=lexemes_list, lexemes_data=lexemes_data, saob_lemma_list=saob_list,
                    saob_data=saob_data)


if __name__ == "__main__":
    main()
