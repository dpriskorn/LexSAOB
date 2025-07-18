from pydantic import BaseModel

from models.wikidata.entity_id import EntityID


class ForeignID(BaseModel):
    id: str
    no_value: bool
    property: str  # This is the property with type ExternalId
    source_item: str  # This is the Q-item for the source

    @property
    def source_item_id(self):
        return EntityID(self.source_item).to_string()

    @property
    def property_id(self):
        return EntityID(self.property).to_string()