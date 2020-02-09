import os
import re
from urllib.request import urlretrieve

from getters.base_getter import BaseGetter
from getters.crossref import Crossref


class ScihubGetter(BaseGetter):
    name = "scihub"
    def __init__(self, visual):
        super().__init__(visual)
        self.base_url = "https://sci-hub.se/"
        self.doi_getter = Crossref(visual)

    def get_bibtex(self, query):
        return []

    def search_pdf(self, entry_title, entry_year):
        # get DOI
        self.visual.log("Looking for entry DOI...")
        doi = self.doi_getter.get_doi(entry_title + " " + entry_year)
        scihub_doc_url = self.base_url + doi
        self.visual.log("Scihub document url resolved to {}".format(scihub_doc_url))
        # download html
        tmpdir = "/tmp/scihub_getter"
        os.makedirs(tmpdir, exist_ok=True)
        self.visual.log("Parsing pdf path...")
        dl_html_path = os.path.join(tmpdir, "html_content")
        urlretrieve(scihub_doc_url, dl_html_path)
        with open(dl_html_path) as f:
            content = f.read()
        pdf_paths = re.findall("https://.*\.pdf", content)
        if not len(pdf_paths):
            return None
        pdf_paths = list(set(pdf_paths))
        if len(pdf_paths) > 1:
            # default to the first path
            pdf_paths = pdf_paths[:1]
        return pdf_paths[0]
