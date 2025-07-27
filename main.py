import logging
from wikibaseintegrator.wbi_config import config as wbconfig

import config
from models.saob_matcher import SaobMatcher

logging.basicConfig(level=config.loglevel)
logger = logging.getLogger(__name__)
wbconfig["USER_AGENT"] = f"LexSAOB User:So9q"

saob = SaobMatcher()
saob.fetch_lexemes_without_saob_id()
saob.run()
