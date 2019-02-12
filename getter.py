import gscholar
from os.path import join
from urllib.request import urlretrieve
import visual
import subprocess
import clipboard


class Getter:
    def __init__(self, conf):
        self.conf = conf
        self.visual = visual.setup(conf)
        pass

    def get_gscholar(self, query):
        self.visual.print("Fetching google scholar content for query: [{}]".format(query))
        res = gscholar.query(query)
        return "\n".join(res)

    def get_web_pdf(self, web_path, entry_id):
        try:
            pdf_dir = self.conf.pdf_dir
            output_path = join(pdf_dir, "{}.pdf".format(entry_id))
            urlretrieve(web_path, output_path)
            self.visual.print("Fetching {} to {}.".format(web_path, output_path))
            return output_path
        except ValueError as ex:
            self.visual.error(ex)
            return None
        except Exception as ex:
            self.visual.error(ex)
            return None

    def search_web_pdf(self, entry_id, entry_title):
        url = self.conf.pdf_search + "+".join(entry_title.split())
        prog = self.conf.browser
        subprocess.run([prog, url])
        self.visual.pause("Copy web pdf path and press enter to continue")
        web_path = clipboard.paste()
        return self.get_web_pdf(web_path, entry_id)
