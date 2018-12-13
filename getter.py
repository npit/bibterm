import gscholar
import visual


class Getter:
    def __init__(self, conf):
        self.conf = conf
        self.visual = visual.setup(conf)
        pass

    def get(self, query):
        self.visual.print("Fetching google scholar content for query: [{}]".format(query))
        res = gscholar.query(query)
        return "\n".join(res)
