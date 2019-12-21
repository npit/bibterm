from urllib.parse import quote, quote_plus

import requests

from getters.base_getter import BaseGetter


class Crossref(BaseGetter):
    name = "crossref"
    num_keep = 5
    def __init__(self, visual):
        super().__init__(visual)
        self.base_url = "https://api.crossref.org/works"


    def get_doi(self, query):
        suff = "?query.bibliographic=" + query + "&select=title,author,DOI&sort=score&order=desc"
        resp = requests.get(self.base_url + suff)
        msg = resp.json()["message"]
        if resp.status_code != 200:
            self.visual.error(msg)
            return None
        data = msg["items"][:self.num_keep]
        if not data:
            return None
        for d in data:
            print(d["title"], d["DOI"])
        data = data[0]
        try:
            return data["DOI"]
        except KeyError:
            return None
