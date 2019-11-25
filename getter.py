import json
import re
import subprocess
from functools import partial
from os import makedirs
from os.path import exists, join
from urllib.parse import quote
from urllib.request import urlretrieve

import bibsonomy
import gscholar

import utils
import visual


class Getter:
    def __init__(self, conf):
        self.conf = conf
        self.visual = visual.setup(conf)
        selected_api = ""

    def configure(self):
        self.apis, self.api_params = zip(*self.conf.pdf_search.items())
        # link to functions
        self.api_funcs = {"bibsonomy": self.get_bibsonomy, "scholar": self.get_scholar}
        for ap, appar in zip(self.apis, self.api_params):
            if ap == "selected_api":
                self.selected_api = appar
                break
        if not self.selected_api:
            self.selected_api = self.visual.ask_user("Select papers on the web using which tool?", "*" + " ".join(self.apis))
            # return True to update config
            return True
        return False

    def get_web_bibtex(self, query):
        try:
            res = self.api_funcs[self.selected_api](query)
        except Exception as ex:
            self.visual.error("Failed to complete the bibtex-fetching query: {}".format(ex))
            return None
        if not res:
            self.visual.error("No data retrieved.")
        return res


    def get_scholar(self, query):
        self.visual.log("Fetching google scholar content for query: [{}]".format(query))
        res = gscholar.query(query)
        return [self.preproc_text(r, do_newline=False) for r in res]

    def preproc_text(self, text, do_newline=True):
        if do_newline:
            text = re.sub("\\n+", " ", text)
            text = re.sub("\n+", " ", text)
        text = re.sub("\t+", " ", text)
        text = re.sub("\s+", " ",text)
        return text

    def get_bibsonomy(self, query, start=0, end=10):
        self.visual.log("Fetching bibsonomy content for query: [{}]".format(query))
        username, apikey = self.api_params[self.apis.index("bibsonomy")]
        rs = bibsonomy.RestSource(username, apikey)
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


    def check_create_pdf_dir(self):
        if not exists(self.conf.pdf_dir):
            if self.visual.yes_no("Pdf directory {} does not exist -- create?".format(self.conf.pdf_dir)):
                makedirs(self.conf.pdf_dir)
                return True
            return False
        return True

    def get_web_pdf(self, web_path, entry_id):
        try:
            if not self.check_create_pdf_dir():
                self.visual.error("pdf directory {} does not exist.".format(self.conf.pdf_dir))
                return None
            output_path = join(self.conf.pdf_dir, "{}.pdf".format(entry_id))
            urlretrieve(web_path, output_path)
            self.visual.log("Fetching {} to {}.".format(web_path, output_path))
            return output_path
        except ValueError as ex:
            self.visual.error(ex)
            return None
        except Exception as ex:
            self.visual.error(ex)
            return None

    def search_web_pdf(self, entry_id, entry_title):
        source_names = list(self.conf.pdf_search)
        source_names[0] = "*" + source_names[0]
        src = self.visual.ask_user("Search for pdf where?", " ".join(source_names))
        if not src:
            self.visual.log("Aborting pdf search.")
            return None
        url = self.conf.pdf_search[src] + "+".join(entry_title.split())
        prog = self.conf.browser
        subprocess.run([prog, url])
        self.visual.pause("Copy web pdf path and press enter to continue")
        web_path = utils.paste()
        if not web_path:
            if self.visual.yes_no("Search for pdf again?"):
                return self.search_web_pdf(entry_id, entry_title)
        return self.get_web_pdf(web_path, entry_id)
