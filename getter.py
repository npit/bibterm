import gscholar
from os.path import join, exists
from os import makedirs
from urllib.request import urlretrieve
import visual
import subprocess
import utils


class Getter:
    def __init__(self, conf):
        self.conf = conf
        self.visual = visual.setup(conf)
        pass

    def get_gscholar(self, query):
        self.visual.log("Fetching google scholar content for query: [{}]".format(query))
        res = gscholar.query(query)
        return "\n".join(res)

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
