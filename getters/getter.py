import itertools
# from functools import partial
from os import makedirs
from os.path import exists, join

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

        if not self.check_create_pdf_dir():
            self.visual.error("Pdf directory {} does not exist nor could it be created.".format(self.conf.pdf_dir))


    def instantiate_selected_apis(self):
        try:
            name, params = self.conf.user_settings["pdf_getter"], self.conf.user_settings["pdf_getter_params"]
            self.pdf_api = self.instantiate_api(name, params)
        except KeyError:
            pass
        except Exception:
            self.visual.error("Failed to instantiate {} api with supplied params {}.".format(name, params))
        try:
            name, params = self.conf.user_settings["bibtex_getter"], self.conf.user_settings["bibtex_getter_params"]
            self.bibtex_api = self.instantiate_api(name, params)
        except KeyError:
            pass
        except Exception:
            self.visual.error("Failed to instantiate {} bibtex api with supplied params {}.".format(name, params))


    def check_bibtex_api(self):
        if not self.bibtex_api:
            res = self.visual.ask_user("Search for bibtex on the web using which tool?", self.bibtex_apis)
            params = self.visual.ask_user("Params?")
            self.bibtex_api = self.instantiate_api(res, params)

    def instantiate_api(self, name, params=None):
        api = self.instantiate(name)
        if not api:
            self.visual.error("Failed to instantiate api {} with supplied params.".format(name))
            return None

        if api.needs_params:
            if params is None:
                self.visual.error("{} api needs parameters to be used.".format(name))
            else:
                api.configure(params)
        return api

    def check_pdf_api(self):
        if not self.pdf_api:
            res = self.visual.ask_user("Search for pdf on the web using which tool?", self.pdf_apis)
            params = self.visual.ask_user("Params?")
            self.pdf_api = self.instantiate_api(res)

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

    def download_web_pdf(self, web_path, entry_id):
        local_output_path = join(self.conf.pdf_dir, "{}.pdf".format(entry_id))
        return self.pdf_api.download_web_pdf(web_path, local_output_path)

    def search_web_pdf(self, entry_id, entry_title, entry_year):
        self.check_pdf_api()
        pdf_web_path = self.pdf_api.search_pdf(entry_title, entry_year)
        return self.download_web_pdf(pdf_web_path, entry_id)
