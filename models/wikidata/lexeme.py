import logging
from datetime import datetime

from pydantic import BaseModel
from wikibaseintegrator.datatypes import ExternalID, Time, Item
from wikibaseintegrator.entities import ItemEntity

import config
from models.wikidata.foreign_id import ForeignID
from models.wikidata.time_format import WikidataTimeFormat

logger = logging.getLogger(__name__)


class Lexeme(BaseModel):
    id: str
    lemma: str
    lexical_category: str

    def url(self):
        return f"{config.wd_prefix}{self.id}"

    def upload_foreign_id_to_wikidata(self,
                                      foreign_id: ForeignID = None):
        """Upload to enrich the wonderfull Wikidata <3"""
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
                time_object = WikidataTimeFormat(datetime=datetime.today())
                date_qualifier = Time(
                    prop_nr="P585",
                    value=time_object.day()
                )
                statement = ExternalID(
                    prop_nr=foreign_id.property,
                    value=None,
                    snak_type="novalue",
                    qualifiers=date_qualifier
                )
                item = ItemEntity(
                    data=[statement],
                    item_id=self.id
                )
                # debug WBI error
                # print(item.get_json_representation())
                result = item.write(
                    edit_summary=f"Added foreign identifier with [[{config.tool_url}]]"
                )
                logger.debug(f"result from WBI:{result}")
                print(self.url())
                #exit(0)
        else:
            # We found the lemma in SAOB
            print(f"Uploading {foreign_id.id} to {self.id}: {self.lemma}")
            statement = ExternalID(
                prop_nr=foreign_id.property,
                value=foreign_id.id,
            )
            described_by_source = Item(
                prop_nr="P1343",  # stated in
                value=foreign_id.source_item_id,
                if_exists="APPEND"
            )
            item = ItemEntity(
                data=[statement,
                      described_by_source],
                item_id=self.id
            )
            # debug WBI error
            # print(item.get_json_representation())
            result = item.write(
                edit_summary=f"Added foreign identifier with [[{config.tool_url}]]"
            )
            logger.debug(f"result from WBI:{result}")
            print(self.url())
            # exit(0)
