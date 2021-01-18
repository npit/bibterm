import itertools
# from functools import partial
from os import makedirs
from os.path import exists, join

import utils
from getters.getterFactory import GetterFactory
from visual import instantiator


class Getter:
    def __init__(self, config):
        self.config = config
        self.visual = instantiator.setup(config)
        self.do_udpate_config = False
        self.browser = "firefox"

        self.bibtex_api, self.pdf_api = None, None
        self.configure()

    def instantiate(self, name):
        return GetterFactory.get_instance(name, self.visual)

    def configure(self):
        try:
            self.browser = self.config.get_user_setting("browser")
        except KeyError:
            pass

        self.pdf_apis = self.config.get_pdf_apis()
        self.bibtex_apis = self.config.get_bibtex_apis()
        self.num_retrieved_bibtex = self.config.get_num_retrieved_bibtex()
        if self.num_retrieved_bibtex is None:
            self.num_retrieved_bibtex = 5
            
        # instantiate user selections
        self.instantiate_selected_apis()

        self.pdf_dir = self.config.get_pdf_dir()
        if not self.check_create_pdf_dir():
            self.visual.error("Pdf directory {} does not exist nor could it be created.".format(self.pdf_dir))


    def instantiate_selected_apis(self):
        try:
            name, params = self.config.get_user_setting("pdf_getter"), self.config.get_user_setting("pdf_getter_params")
            self.pdf_api = self.instantiate_api(name, params)
        except KeyError:
            pass
        except Exception:
            self.visual.error("Failed to instantiate pdf api: [{}]  with supplied params: {}.".format(name, params))
        try:
            name, params = self.config.get_user_setting("bibtex_getter"), self.config.get_user_setting("bibtex_getter_params")
            self.bibtex_api = self.instantiate_api(name, params)
        except KeyError:
            pass
        except Exception:
            self.visual.error("Failed to instantiate  bibtex api: [{}] with supplied params: {}.".format(name, params))


    def bibtex_api_configured(self):
        while self.bibtex_api is None:
            res = self.visual.ask_user("Search for bibtex on the web using which tool?", self.bibtex_apis)
            if res == "q":
                return False
            params = self.visual.ask_user("Params?")
            self.bibtex_api = self.instantiate_api(res, params)
        return True

    def instantiate_api(self, name, params=None):
        api = self.instantiate(name)
        if not api:
            # self.visual.error("Failed to instantiate api {} with supplied params.".format(name))
            return None

        if api.needs_params:
            if params is None:
                self.visual.error("{} api needs parameters to be used.".format(name))
            else:
                api.configure(params)
        return api

    def pdf_api_configured(self):
        while self.pdf_api is None:
            res = self.visual.ask_user("Search for pdf on the web using which tool?", self.pdf_apis)
            if res == "q":
                return False
            params = self.visual.ask_user("Params?")
            self.pdf_api = self.instantiate_api(res, params)
        return True

    def check_create_pdf_dir(self):
        if not exists(self.pdf_dir):
            if self.visual.yes_no("Pdf directory {} does not exist -- create?".format(self.pdf_dir)):
                makedirs(self.pdf_dir)
                return True
            return False
        return True

    def get_web_bibtex(self, query):
        if not self.bibtex_api_configured():
            return None
        res = self.bibtex_api.get_web_bibtex(query)
        if res:
            res = res[:self.num_retrieved_bibtex]
        return res

    def download_web_pdf(self, web_path, entry_id):
        local_output_path = join(self.pdf_dir, "{}.pdf".format(entry_id))
        return self.pdf_api.download_web_pdf(web_path, local_output_path)

    def search_web_pdf(self, entry_id, entry_title, entry_year):
        breakpoint()
        if not self.pdf_api_configured():
            return None
        pdf_web_path = self.pdf_api.search_pdf(entry_title, entry_year)
        return self.download_web_pdf(pdf_web_path, entry_id)
