from getters.base_getter import BaseGetter


class BibsonomyGetter(BaseGetter):
    name = "bibsonomy"
    def __init__(self, params, visual):
        super().__init__(visual)
        self.base_url = "https://sci-hub.tw"

    def get_bibtex(self, query):
        return []
