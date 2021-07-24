class SAOBEntry():
    id: str = None
    lemma: str = None
    lexical_category: str = None
    number: int = None

    def __init__(self,
                 id: str = None,
                 lemma: str = None,
                 lexical_category: str = None,
                 number: int = None):
        self.id = id
        self.lemma = lemma
        self.lexical_category = lexical_category
        self.number = number