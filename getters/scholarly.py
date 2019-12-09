import scholarly
from getters.base_getter import BaseGetter


class ScholarlyGetter(BaseGetter):
    name = "scholarly"

    def __init__(self, visual):
        super().__init__(visual)
        self.base_url = None

    def map_keys(self, ddict):
        for k in ddict:
            if k == 'bibtexKey':
                ddict['ID'] = ddict[k]
                del ddict[k]
        first_author = ddict["author"].split()[0].lower()
        first_title_word = ddict["title"].split()[0].lower()
        year = "XXXX"
        ddict["ID"] = "{}{}{}".format(first_author, year, first_title_word)
        return ddict

    def get_bibtex(self, query):
        res = []
        gtor = scholarly.search_pubs_query(query)
        for i, x in enumerate(gtor):
            if i > 10:
                break;
            ddict = x.bib
            res.append(ddict)
        return res
