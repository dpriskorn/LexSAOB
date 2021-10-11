import os

# Add your credentials from the botpasswords page to your ~/.bashrc or below as
# strings:
username = ""
password = ""

# Global variables
count_only = False
add_no_value = True
match_subentry = False
login_instance = None
loglevel = None
tool_url = "Wikidata:Tools/LexSAOB"
wd_prefix = "http://www.wikidata.org/entity/"
supported_by_saob = "abcdefghijklmnopqrstu-"
ask_when_no_category_found = False