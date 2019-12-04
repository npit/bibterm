import gscholar
from getters.base_getter import BaseGetter


class gScholarGetter(BaseGetter):
    name = "gscholar"
    def __init__(self, visual):
        super().__init__(visual)
        self.base_url = None

    def get_bibtex(self, query):
        self.visual.log("Fetching google scholar content for query: [{}]".format(query))
        res = gscholar.query(query)
        return [self.preproc_text(r, do_newline=False) for r in res]
