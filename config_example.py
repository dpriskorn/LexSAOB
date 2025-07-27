# Add your credentials from the botpasswords page to your ~/.bashrc or below as
# strings:
import logging

# botpassword login
user_name = ""
bot_password = ""
user_name_only = "" # enter your username here

# Global variables
loglevel = logging.WARN
tool_url = "Wikidata:Tools/LexSAOB"
wd_prefix = "http://www.wikidata.org/entity/"
press_enter_to_continue = True
lexeme_fetch_limit = 10
saob_main_entry_property: str = "P8478"  # SAOB main entry
saob_subentry_property: str = "P9963"
dictionary_item: str = "Q1935308"  # SAOB
query_format_url: str = "https://www.saob.se/artikel/?seek="
processed_lexeme_ids = "processed_lexeme_ids.csv"