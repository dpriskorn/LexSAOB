#!/usr/bin/env python3
# Licensed under GPLv3+ i.e. GPL version 3 or later.
import logging
from urllib.parse import urlparse, parse_qsl
from pprint import pprint
from csv import reader

from wikibaseintegrator import wbi_core, wbi_login

import config
import loglevel

# Constants
wd_prefix = "http://www.wikidata.org/entity/"

print("Logging in with Wikibase Integrator")
login_instance = wbi_login.Login(
    user=config.username, pwd=config.password
)
# open file in read mode
with open('saob_2021-01-06.csv', 'r') as read_obj:
    # pass the file object to reader() to get the reader object
    csv_reader = reader(read_obj)
    # Iterate over each row in the csv using reader object
    for row in csv_reader:
        # row variable is a list that represents a row in csv
        # debug:
        print(row)
        #*********************
        # Set up the variables
        #*********************
        #row0 is null
        word = row[1]
        saob_category = row[2]
        number = row[3]
        if number != "":
            #skip complexity for now
            continue
        url = urlparse(row[4])
        # print(url.query)
        saob_id = dict(parse_qsl(url.query))["id"]
        # print(saob_id)
        # match the lexical category
        has_saob_category = True
        category = ""
        if saob_category == "":
            no_category = False
        elif saob_category == "verb":
            category = "Q24905"
        elif saob_category == "subst":
            category = "Q1084"
        elif saob_category == "adj":
            category = "Q34698"
        elif saob_category == "adv":
            category = "Q380057"
        else:
            # unsupported category provided
            #skip complexity for now
            continue
        print(category)
        #exit(0)
        #********************************
        # Search for the word using sparql
        #********************************
        if has_saob_category:
            print("debug")
            data = wbi_core.ItemEngine.execute_sparql_query(f"""
            select ?lexemeId ?lemma

        WHERE {{
          #hint:Query hint:optimizer "None".
          ?lexemeId dct:language wd:Q9027;
                    wikibase:lemma ?lemma;
                    wikibase:lexicalCategory wd:{category}.
          FILTER(STR(?lemma) = "{word}").
          MINUS{{
            ?lexemeId wdt:P8478 [].
          }}
        }}
        """)
        else:
            # no SAOB category
            data = wbi_core.ItemEngine.execute_sparql_query(f"""
            select ?lexemeId ?lemma

        WHERE {{
          #hint:Query hint:optimizer "None".
          ?lexemeId dct:language wd:Q9027;
                    wikibase:lemma ?lemma.
          FILTER(STR(?lemma) = "{word}").
          MINUS{{
            ?lexemeId wdt:P8478 [].
          }}
        }}
           """)
        results = data["results"]["bindings"]
        # pprint(results)
        if len(results) == 0:
            print("No lexeme found")
        else:
            for result in results:
                #*************************
                # Handle result and upload
                #*************************
                lemma = result["lemma"]["value"]
                lid = result["lexemeId"]["value"].replace(wd_prefix, "")
                print(f"Hittade {lid}: {lemma}")
                # TODO if numbered
                # - fetch lexeme using wbi
                # - present to user
                # - ask user which if one matches
                print(f"Adding {saob_id} to {lid}")
                saob_statement = wbi_core.ExternalID(
                    prop_nr="P8478",
                    value=saob_id,
                )
                described_by_source = wbi_core.ItemID(
                    prop_nr="P1343",
                    value="Q1935308"
                )
                item = wbi_core.ItemEngine(
                    data=[saob_statement,
                          described_by_source],
                    #append_value="P8478",
                    item_id=lid
                )
                result = item.write(
                    login_instance,
                    edit_summary="Added SAOB identifier with [[Wikidata:LexSAOB]]"
                )
                #if config.debug_json:
                #logging.debug(f"result from WBI:{result}")
                print(f"{wd_prefix}{lid}")
