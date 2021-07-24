class Lexeme():
    id: str = None
    lemma: str = None
    lexical_category: str = None

    def __init__(self,
                 id: str = None,
                 lemma: str = None,
                 lexical_category: str = None):
        self.id = id
        self.lemma = lemma
        self.lexical_category = lexical_category