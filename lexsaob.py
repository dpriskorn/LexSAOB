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
#download all swedish lexemes via sparql (~23000 as of 2021-04-05)
#dictionary with word as key and list in the value
#list[0] = lid
#list[1] = category Qid
print("Fetching all lexemes")
lexemes_data = {}
lexemes_list = []
for i in range(0,10000,10000):
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
        print("adding lexemes to list")
        pprint(results.keys())
        pprint(results["results"].keys())
        pprint(len(results["results"]["bindings"]))
        for result in results["results"]["bindings"]:
            #print(result)
            #*************************
            # Handle result and upload
            #*************************
            lemma = result["lemma"]["value"]
            lid = result["lexemeId"]["value"].replace(wd_prefix, "")
            category = result["category"]["value"].replace(wd_prefix, "")
            lexemes_data[lemma] = [lid, category]
            lexemes_list.append(lemma)
print(f"{len(lexemes_list)} fetched")
# exit(0)
# load all saab words into a list that can be searched
# load all saab ids into a list we can lookup in using the index.
# the two lists above have the same index.
# load all saob lines into a dictionary with count as key and list in the value
#list[0] = saob_category
#list[1] = number
#list[2] = id
#list[3] = word
print("Loading SAOB into memory")
saob_wordlist = []
saob_data = {}
# open file in read mode
with open('saob_2021-01-06.csv', 'r') as read_obj:
    # pass the file object to reader() to get the reader object
    csv_reader = reader(read_obj)
    count = 0
    # Iterate over each row in the csv using reader object
    for row in csv_reader:
        # row variable is a list that represents a row in csv
        # debug:
        #print(row)
        #*********************
        # Set up the variables
        #*********************
        #row0 is null
        word = row[1]
        saob_category = row[2]
        if row[3] == '':
            number = 0
        else:
            number = int(row[3])
        url = urlparse(row[4])
        # print(url.query)
        saob_id = dict(parse_qsl(url.query))["id"]
        saob_data[count] = [saob_category, number, saob_id, word]
        saob_wordlist.append(word)
        count += 1
print(f"loaded {count} saob lines into dictionary with length {len(saob_data)}")
print(f"loaded {count} saob lines into list with length {len(saob_wordlist)}")
# exit(0)
# go through all lexemes missing SAOB identifier
for lexeme in lexemes_list:
    #lookup
    lexeme_data = lexemes_data[lexeme]
    print(f"Working on {lexeme_data[0]}: {lexeme}")
    value_count = 0
    saob_indexes = []
    if lexeme in saob_wordlist:
        for count, value in enumerate(saob_wordlist):
            if value == lexeme:
                print(count, value)
                saob_indexes.append(count)
                value_count += 1
        if value_count > 1:
            print(f"Found more than 1 value = complex, skipping")
        elif value_count == 1:
            saob_worddata = saob_data[saob_indexes[0]]
            saob_category = saob_worddata[0]
            number = saob_worddata[1]
            saob_id = saob_worddata[2]
            if number != 0:
                print(f"Found number > 0 = complex, skipping")
            else:
                print(f"found match: category: {saob_worddata[0]} id: {saob_worddata[2]}")
                #check if categories match
                category = None
                if saob_category == "verb":
                    category = "Q24905"
                elif saob_category == "subst":
                    category = "Q1084"
                elif saob_category == "adj":
                    category = "Q34698"
                elif saob_category == "adv":
                    category = "Q380057"
                else:
                    print(f"Did not recognize category {saob_category}, skipping")
                if category is not None:
                    if category == lexeme_data[1]:
                        print("Hooray categories match, uploading")
                        #*************************
                        # upload
                        #*************************
                        lemma = lexeme
                        lid = lexeme_data[0]
                        print(f"Uploading id to {lid}: {lemma}")
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
                            edit_summary="Added SAOB identifier with [[Wikidata:Tools/LexSAOB]]"
                        )
                        #if config.debug_json:
                        #logging.debug(f"result from WBI:{result}")
                        print(f"{wd_prefix}{lid}")
                        exit(0)
                    else:
                        print("Categories did not match :/ - skipping")
    else:
        print(f"{lexeme} not found in SAOB wordlist")
