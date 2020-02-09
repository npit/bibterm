import subprocess

import utils
from getters.base_getter import BaseGetter


class ScholarGetter(BaseGetter):
    name = "scholar"
    def __init__(self, visual):
        super().__init__(visual)
        self.base_url = "https://scholar.google.com/scholar?hl=en&q="
        self.needs_params = True

    def configure(self, params):
        self.browser = params


    def search_pdf(self, entry_title, entry_year):
        url = self.get_url(entry_title)
        try:
            subprocess.run([self.browser, url])
        except Exception as ex:
            self.visual.error(ex)
            return None

        web_pdf_path = None
        while True:
            self.visual.pause("Copy web pdf path and press enter to continue")
            web_pdf_path = utils.paste()
            if not web_pdf_path:
                if not self.visual.yes_no("Empty path -- retry?"):
                    return None
            else:
                return web_pdf_path
