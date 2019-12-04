import scholarly
from getters.base_getter import BaseGetter


class ScholarlyGetter(BaseGetter):
    name = "scholarly"

    def __init__(self, visual):
        super().__init__(visual)
        self.base_url = None

    def get_bibtex(self, query):
        res = []
        gtor = scholarly.search_pubs_query(query)
        for i, x in enumerate(gtor):
            if i > 10:
                break;
            res.append(x.bib)
        return res
