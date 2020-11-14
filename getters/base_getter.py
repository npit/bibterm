import re
import string
from urllib.request import urlretrieve


class BaseGetter:

    def __init__(self, visual):
        self.visual = visual
        self.needs_params = False
        self.base_url = ""

    def get_url(self, query):
        return self.base_url + query

    def get_bibtex(self, query):
        self.visual.error(f"Getter {self.name} cannot search for bibtexs!")
        pass

    def get_params(self):
        return ""

    def configure(self, params):
        pass

    def get_web_bibtex(self, query):
        try:
            self.visual.log("Searching bibtex with {}...".format(self.name))
            res = self.get_bibtex(query)
        except Exception as ex:
            self.visual.error("Failed to complete the bibtex-fetching query. Reason: {}".format(ex))
            return []
        if res is None:
            res = []
        return res

    # simple file downloader for directly linked files
    def download_web_pdf(self, web_path, output_path):
        self.visual.log("Fetching {} to {}.".format(web_path, output_path))
        try:
            urlretrieve(web_path, output_path)
            return output_path
        except ValueError as ex:
            self.visual.error(ex)
            return None
        except Exception as ex:
            self.visual.error(ex)
            return None

    def preproc_text(self, text, do_newline=True):
        if do_newline:
            text = re.sub("\\n+", " ", text)
            text = re.sub("\n+", " ", text)
        text = re.sub("\t+", " ", text)
        text = re.sub("\s+", " ",text)
        return text

    # get a dict key, if it exists, else None
    def remove_punct(self, text):
        text = re.sub("[" + string.punctuation + "]", " ", text)
        return re.sub("[ ]+", " ", text)
