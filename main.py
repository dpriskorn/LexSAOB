import logging
from wikibaseintegrator.wbi_config import config as wbconfig

import config
from models.saob_matcher import SaobMatcher

logging.basicConfig(level=config.loglevel)
logger = logging.getLogger(__name__)
wbconfig["USER_AGENT"] = f"LexSAOB User:So9q"
# wbconfig['MEDIAWIKI_API_URL'] = 'https://test.wikidata.org/w/api.php'

# test of login
# from wikibaseintegrator import wbi_login
# login_instance = wbi_login.Login(user=config.user_name, password=config.bot_password)
# exit(0)


saob = SaobMatcher()
saob.fetch_lexemes_without_saob_id()
#print(saob.lids)
#exit(0)
saob.run()
