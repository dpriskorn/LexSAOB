from pydantic import BaseModel

import config
from models.wikidata.entity_id import EntityID


class ForeignID(BaseModel):
    id: str = ""
    no_value: bool = False
    property_: str  # This is the property with type ExternalId

    @property
    def property_id(self):
        return EntityID(self.property_).to_string()