import json
import re
from urllib.parse import quote

import bibsonomy
import utils
from getters.base_getter import BaseGetter


class BibsonomyGetter(BaseGetter):
    name = "bibsonomy"
    def __init__(self, visual):
        super().__init__(visual)
        self.base_url = "https://www.bibsonomy.org/search/"
        self.needs_params = True

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


    def get_bibtex(self, query):
        self.visual.log("Fetching bibsonomy content for query: [{}]".format(query))
        rs = bibsonomy.RestSource(self.username, self.api_key)
        # def func(q, start=0, end=1000):
        #     return rs._get("/posts?resourcetype=" + quote(rs._get_resource_type("publication")) + "&search={}".format(q))
        res = rs._get("/posts?resourcetype=" + quote(rs._get_resource_type("publication")) + "&search={}".format(query))
        res = json.loads(res)
        if res['stat'] != 'ok':
            self.visual.error("Error fetching bibsonomy query '{}' : {}".format(query, res['stat']))
            return None
        res = res['posts']['post']
        res = [res[i]["bibtex"] for i in range(len(res))]
        res = [{k: self.preproc_text(dct[k]) for k in dct} for dct in res]
        return sorted(res, key=lambda x: x['year'] if 'year' in x else x['title'])
