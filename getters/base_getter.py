import re
import string


class BaseGetter:

    def __init__(self, visual):
        self.visual = visual
        self.needs_params = False

    def get_url(self, query):
        return self.base_url + query

    def get_bibtex(self, query):
        pass

    def configure(self, query):
        pass

    def get_web_bibtex(self, query):
        try:
            self.visual.log("Searching bibtex with {}...".format(self.name))
            res = self.get_bibtex(query)
        except Exception as ex:
            self.visual.error("Failed to complete the bibtex-fetching query. Reason: {}".format(ex))
            return None
        if not res:
            self.visual.error("No data retrieved.")
        return res

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
