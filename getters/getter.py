import itertools
import subprocess
# from functools import partial
from os import makedirs
from os.path import exists, join
from urllib.request import urlretrieve

import utils
import visual
from getters.getterFactory import GetterFactory


class Getter:
    def __init__(self, conf):
        self.conf = conf
        self.visual = visual.setup(conf)
        self.do_udpate_config = False
        self.browser = "firefox"

        self.bibtex_api, self.pdf_api = None, None
        self.configure()

    def instantiate(self, name):
        return GetterFactory.get_instance(name, self.visual)

    def get_selected_apis(self):
        ret = {}
        if self.pdf_api is not None:
            ret["pdf_getter"] = self.pdf_api.name
        if self.bibtex_api is not None:
            ret["bibtex_getter"] = self.bibtex_api.name
            if self.bibtex_api.needs_params:
                ret["bibtex_getter_params"] = self.bibtex_api.get_params()
        return ret

    def configure(self):
        try:
            self.browser = self.conf.user_settings["browser"]
        except KeyError:
            pass

        self.pdf_apis = self.conf.pdf_apis
        self.bibtex_apis = self.conf.bibtex_apis
        self.num_retrieved_bibtex = self.conf.num_retrieved_bibtex

        # instantiate user selections
        self.instantiate_selected_apis()


    def instantiate_selected_apis(self):
        if "bibtex_getter" in self.conf.user_settings:
            name, params = self.conf.user_settings["bibtex_getter"], None
            try:
                params = self.conf.user_settings["bibtex_getter_params"]
            except KeyError:
                pass
            self.instantiate_bibtex_api(name, params)

        if "pdf_getter" in self.conf.user_settings:
            self.instantiate_pdf_api(self.conf.user_settings["pdf_getter"])

    def check_bibtex_api(self):
        if not self.bibtex_api:
            res = self.visual.ask_user("Search for bibtex on the web using which tool?", self.bibtex_apis)
            self.instantiate_bibtex_api(res)

    def instantiate_bibtex_api(self, name, params):
        self.bibtex_api = self.instantiate(name)
        if not self.bibtex_api:
            self.visual.error("Failed to instantiate bibtex api {} with supplied params.".format(name))
            return None

        if self.bibtex_api.needs_params:
            if "bibtex_getter_params" in self.conf.user_settings:
                self.bibtex_api.configure(params)
            else:
                self.visual.error("{} bibtex api needs parameters to be used.".format(self.bibtex_api.name))


    def check_pdf_api(self):
        if not self.pdf_api:
            res = self.visual.ask_user("Search for pdf on the web using which tool?", self.pdf_apis)
            self.instantiate_pdf_api(res)

    def instantiate_pdf_api(self, name):
        self.pdf_api = self.instantiate(name)
        if not self.pdf_api:
            self.visual.error("Failed to instantiate pdf api {}.".format(name))
            return None

    def check_create_pdf_dir(self):
        if not exists(self.conf.pdf_dir):
            if self.visual.yes_no("Pdf directory {} does not exist -- create?".format(self.conf.pdf_dir)):
                makedirs(self.conf.pdf_dir)
                return True
            return False
        return True

    def get_web_bibtex(self, query):
        self.check_bibtex_api()
        res = self.bibtex_api.get_web_bibtex(query)
        if res:
            res = res[:self.num_retrieved_bibtex]
        return res

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
        self.check_pdf_api()
        url = self.pdf_api.get_url(entry_title)
        subprocess.run([self.browser, url])
        self.visual.pause("Copy web pdf path and press enter to continue")
        web_path = utils.paste()
        if not web_path:
            if self.visual.yes_no("Search for pdf again?"):
                return self.search_web_pdf(entry_id, entry_title)
        return self.get_web_pdf(web_path, entry_id)
