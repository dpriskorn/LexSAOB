#!/usr/bin/env python3
# Licensed under GPLv3+ i.e. GPL version 3 or later.
import logging
from csv import reader
from typing import List, Dict
from urllib.parse import urlparse, parse_qsl

from wikibaseintegrator import wbi_config
from wikibaseintegrator import wbi_login, wbi_datatype

import config
from helpers.console import ask_yes_no_question, console
from helpers.wbi_helper import time_today_statement
from models import wikidata, saob
from models.saob import SAOBSubentry
from models.wikidata import LexemeLanguage, ForeignID

wd_prefix = "http://www.wikidata.org/entity/"

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


# Pseudo code
# first it gets all swedish lexemes
# opens the list of entries in SAOB
# tries to match each lexeme to an entry
# if match found
## uploads
# else
# add no-value to the lexeme


def handle_no_category(lexeme: wikidata.Lexeme = None,
                       saob_entry: saob.SAOBEntry = None):
    if lexeme is None:
        raise ValueError("lexeme was None")
    category = None
    logging.info("No category found")
    if config.ask_when_no_category_found:
        # TODO improve this by scraping from SAOB
        if lexeme.lexical_category == "Q1084":
            answer = ask_yes_no_question(f"Is {saob_entry.lemma} a noun? ({saob_entry.url()})")
            if answer:
                category = "Q1084"
        if lexeme.lexical_category == "Q24905":
            answer = ask_yes_no_question(f"Is {saob_entry.lemma} a verb? ({saob_entry.url()})")
            if answer:
                category = "Q24905"
        if lexeme.lexical_category == "Q34698":
            answer = ask_yes_no_question(f"Is {saob_entry.lemma} an adjective? ({saob_entry.url()})")
            if answer:
                category = "Q34698"
        if lexeme.lexical_category == "Q380057":
            answer = ask_yes_no_question(f"Is {saob_entry.lemma} an adverb? ({saob_entry.url()})")
            if answer:
                category = "Q380057"
    return category


def check_matching_category(lexeme: wikidata.Lexeme = None,
                            saob_entry: saob.SAOBEntry = None,
                            unrecognized_category_count: int = None) -> [bool, bool]:
    logger = logging.getLogger(__name__)
    if lexeme is None or saob_entry is None:
        raise ValueError("Did not get the arguments needed")
    # TODO find out what the number means and how it affects the matching
    logger.debug(f"SAOB number: {saob_entry.number}")
    logger.debug(f"found match: category: {saob_entry.lexical_category} id: {saob_entry.id}")
    category = handle_no_category(lexeme=lexeme,
                                  saob_entry=saob_entry)
    # check if categories match
    if "verb" in saob_entry.lexical_category:
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
        return False, False
    else:
        logging.error(f"Did not recognize category "
                      f"'{saob_entry.lexical_category}' on {saob_entry.lemma} "
                      f"({saob_entry.url()}), skipping (in total skipped: {unrecognized_category_count})")
        return False, True
    if category is not None:
        if category == lexeme.lexical_category:
            return True, False
        else:
            logging.info("Categories did not match, skipping")
            return False, False


def load_saob_into_memory():
    # load all saab words into a list that can be searched
    # load all saab ids into a list we can lookup in using the index.
    # the two lists above have the same index.
    # load all saob lines into a dictionary with count as key and list in the value
    # list[0] = saob_category
    # list[1] = number
    # list[2] = id
    # list[3] = word
    print("Loading SAOB into memory")
    saob_lemma_list = []
    saob_data = {}
    # open file in read mode
    with open('saob_2021-08-13.csv', 'r') as read_obj:
        # pass the file object to reader() to get the reader object
        csv_reader = reader(read_obj)
        count = 0
        # Iterate over each row in the csv using reader object
        for row in csv_reader:
            # row variable is a list that represents a row in csv
            # row0 is null
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
            entry = saob.SAOBEntry(
                id=saob_id,
                lexical_category=saob_category,
                number=saob_number,
                lemma=word
            )
            saob_data[count] = entry  # [saob_category, saob_number, saob_id, word]
            saob_lemma_list.append(word)
            count += 1
    logger.info(f"loaded {count} saob lines into dictionary with length {len(saob_data)}")
    logger.info(f"loaded {count} saob lines into list with length {len(saob_lemma_list)}")
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
    no_value_count = 0
    unrecognized_category_count = 0
    for lemma in lexeme_lemma_list:
        if processed_count > 0 and processed_count % 1000 == 0:
            print(f"Processed {processed_count} lexemes out of "
                  f"{lexemes_count} ({round(processed_count * 100 / lexemes_count)}%)")
        lexeme: wikidata.Lexeme = lexemes_data[lemma]
        logging.info(f"Working on {lexeme.id}: {lexeme.lemma} {lexeme.lexical_category} {lexeme.url()}")
        value_count = 0
        matching_saob_indexes = []
        if lexeme.lemma in saob_lemma_list:
            # Count number of hits
            for count, saob_lemma in enumerate(saob_lemma_list):
                if saob_lemma == lexeme.lemma:
                    # print(count, value)
                    matching_saob_indexes.append(count)
                    value_count += 1
            if value_count > 1:
                logger.debug(f"Found more than 1 matching lemma = complex")
                adj_count = 0
                subst_count = 0
                verb_count = 0
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
                    result, unrecognized_category = check_matching_category(
                        lexeme=lexeme,
                        saob_entry=entry,
                        unrecognized_category_count=unrecognized_category_count
                    )
                    if unrecognized_category:
                        unrecognized_category_count += 1
                    if result:
                        logging.info("Categories match")
                        match_count += 1
                        # sometimes the saob categories have a "." after the category
                        if "subst" in entry.lexical_category:
                            if subst_count > 1:
                                logging.info("More that one noun found. Skipping")
                                skipped_multiple_matches += 1
                                continue
                            if subst_count == 0:
                                logging.info("Possibly more that one noun found. Skipping")
                                skipped_multiple_matches += 1
                                continue
                        if "verb" in entry.lexical_category:
                            if verb_count > 1:
                                logging.info("More that one verb found. Skipping")
                                skipped_multiple_matches += 1
                                continue
                        if "adj" in entry.lexical_category:
                            if adj_count > 1:
                                logging.info("More that one adj found. Skipping")
                                skipped_multiple_matches += 1
                                continue
                        # TODO scrape entry definitions from saob and let the user decide
                        # whether any match the senses of the lexeme if any
                        # answer = ask_yes_no_question(f"Do you want to upload {entry.lemma} "
                        #                              f"({entry.url()}) to {lexeme.lemma} "
                        #                              f"({lexeme.url()})?")
                        console.print("Found unique match between lemma and lexical category")
                        lexeme.upload_foreign_id_to_wikidata(foreign_id=ForeignID(
                            id=entry.id,
                            property="P8478",
                            source_item_id="Q1935308"
                        ))
            elif value_count == 1:
                # Only 1 search result in the saob wordlist so pick it
                entry = saob_data[matching_saob_indexes[0]]
                logger.info(f"Only 1 matching lemma, see {entry.url()}")
                result, unrecognized_category = check_matching_category(
                    lexeme=lexeme,
                    saob_entry=entry,
                    unrecognized_category_count=unrecognized_category_count
                )
                if unrecognized_category:
                    unrecognized_category_count += 1
                if result:
                    match_count += 1
                    lexeme.upload_foreign_id_to_wikidata(foreign_id=ForeignID(
                        id=entry.id,
                        property="P8478",
                        source_item_id="Q1935308"
                    ))
        else:
            logging.debug(f"{lexeme.lemma} not found in SAOB wordlist")
            # if config.add_no_value:
            #     # Add SAOB=no_value to lexeme
            #     lexeme.upload_foreign_id_to_wikidata(foreign_id=ForeignID(
            #         property="P8478",
            #         no_value=True
            #     ))
            # no_value_count += 1
            if config.match_subentry:
                if lexeme.lemma[:1] not in config.supported_by_saob:
                    logger.debug("Skip searhing for this because "
                                 "SAOB only published lemma from a-u.")
                else:
                    logger.info("Searching for the lemma on saob.se to find a subentry")
                    subentry = SAOBSubentry(lexeme.lemma)
                    found = subentry.search_using_api()
                    if found:
                        logger.info(f"Found subentry match for {lexeme.lemma}")
                        # Add new property (to be proposed) SAOB section ID
                        print(subentry)
                        lexeme.upload_foreign_id_to_wikidata(foreign_id=ForeignID(
                            id=f"{subentry.lemma}#{subentry.section_id}",
                            property="P9963",
                            source_item_id="Q1935308"
                        ))
                        # logger.debug("debug exit 4")
                        # exit(0)
                    else:
                        # Add SAOB section ID=no_value to lexeme
                        logger.info(f"No subentry match for {lexeme.lemma}")
                        lexeme.upload_statement_to_wikidata(statement=wbi_datatype.ItemID(
                            prop_nr="P9660",
                            value="Q1935308",
                            qualifiers=[time_today_statement()]
                        ))
                        # logger.debug("debug exit here")
                        # exit(0)
        processed_count += 1
    print(f"Processed {processed_count} lexemes. "
          f"Found {match_count} matches "
          f"out of which {skipped_multiple_matches} "
          f"was skipped because they had multiple entries "
          f"with the same lexical category. {no_value_count} "
          f"entries with no main entry in SAOB was found")


def main():
    print("Logging in with Wikibase Integrator")
    config.login_instance = wbi_login.Login(
        user=config.username, pwd=config.password
    )
    # Set User-Agent
    wbi_config.config["USER_AGENT_DEFAULT"] = f"LexSAOB (WikidataIntegrator/0.11.0) User:So9q"
    language = LexemeLanguage("sv")
    language.fetch_all_lexemes_without_saob_id()
    lexemes_list = language.lemma_list()
    lexemes_data = language.data_dictionary_with_lemma_as_key()
    saob_list, saob_data = load_saob_into_memory()
    process_lexemes(lexeme_lemma_list=lexemes_list, lexemes_data=lexemes_data, saob_lemma_list=saob_list,
                    saob_data=saob_data)


if __name__ == "__main__":
    main()
