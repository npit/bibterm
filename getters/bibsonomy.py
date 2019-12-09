import json
import re
from urllib.parse import quote, quote_plus

import bibsonomy
import utils
from getters.base_getter import BaseGetter


class BibsonomyGetter(BaseGetter):
    name = "bibsonomy"
    def __init__(self, visual):
        super().__init__(visual)
        self.base_url = "https://www.bibsonomy.org/search/"
        self.needs_params = True
        self.ignore_keys = "intrahash interhash href misc bibtexAbstract".split()
        self.dont_preproc_keys = "author".split()

    def get_params(self, params):
        return [self.username, self.api_key]

    def configure(self, params):
        try:
            self.username, self.api_key = params
        except ValueError:
            self.visual.fatal_error("Bibsonomy parameters need to be a string list with the username and the api key")

    def get_url(self, query):
        # bibsonomy does not like punctuation
        return super().get_url(self.remove_punct(query))

    def process_query(self, query):
        return " ".join((self.remove_punct(query).split()))

    def map_keys(self, ddict):
        rdict = {k: v for (k, v) in ddict.items()}
        for k in ddict:
            if k == 'bibtexKey':
                rdict['ID'] = rdict[k]
                del rdict[k]
            if k == self.ignore_keys:
                del rdict[k]
            if k == "author":
                rdict[k] = [x.strip() for x in rdict[k].split("and")]
        return rdict

    def get_bibtex(self, query):
        self.visual.log("Fetching bibsonomy content for query: [{}]".format(query))
        rs = bibsonomy.RestSource(self.username, self.api_key)
        query = self.process_query(query)
        # def func(q, start=0, end=1000):
        #     return rs._get("/posts?resourcetype=" + quote(rs._get_resource_type("publication")) + "&search={}".format(q))
        res = rs._get("/posts?resourcetype=" + quote(rs._get_resource_type("publication")) + "&search={}".format(quote_plus(query)))
        res = json.loads(res)
        if res['stat'] != 'ok':
            self.visual.error("Error fetching bibsonomy query '{}' : {}".format(query, res['stat']))
            return None
        res = res['posts']['post']
        res = [self.map_keys(res[i]["bibtex"]) for i in range(len(res))]
        res = [{k: self.preproc_text(dct[k]) if k not in self.dont_preproc_keys else dct[k] for k in dct} for dct in res]
        return sorted(res, key=lambda x: x['year'] if 'year' in x else x['title'])
