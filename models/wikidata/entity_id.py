from models.wikidata.enums import WikidataNamespaceLetters


class EntityID:
    letter: WikidataNamespaceLetters
    number: int

    def __init__(self,
                 entity_id: str = None):
        if entity_id is not None:
            if len(entity_id) > 1:
                self.letter = WikidataNamespaceLetters(entity_id[0])
                self.number = int(entity_id[1:])
            else:
                raise Exception("Entity ID was too short.")
        else:
            raise Exception("Entity ID was None")

    def to_string(self):
        return f"{self.letter.value}{self.number}"
