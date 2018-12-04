import pandas
from collections import namedtuple
from fuzzywuzzy import process

# do not use curses, try
#     http: // urwid.org / tutorial /
#     or
#     https: // pypi.org / project / blessings /

def loop(runner):
    runner.loop()

class Entry:
    ENTRYTYPE = None
    ID = None
    archiveprefix = None
    arxivid = None
    author = None
    booktitle = None
    doi = None
    eprint = None
    file = None
    isbn = None
    issn = None
    keywords = None
    link = None
    number = None
    pages = None
    pmid = None
    publisher = None
    title = None
    url = None
    volume = None
    year = None
    def __init__(self, kv):
        for key in kv:
            self.__setattr__(key, kv[key])
    def has_keywords(self):
        return self.keywords is not None
    def has_keyword(self, kw):
        if not self.has_keywords():
            return False
        return kw in self.keywords


# base class to get and print stuff
class Visualizer:
    def idle(self):
        print("Give command.")
    def print(self, msg):
        print(msg)
    def input(self,msg=""):
        return input(msg)
    def search(self, query, candidates, atmost):
        return process.extract(query, candidates, limit=atmost)
    def newline(self):
        print()


class Blessings(Visualizer):
    def idle(self):
        print("Give command.")
    def print(self, msg):
        print(msg)
    def input(self,msg=""):
        return input(msg)
    def search(self, query, candidates, atmost):
        return process.extract(query, candidates, limit=atmost)
    def newline(self):
        print()


class Runner:

    commands = namedtuple("commands", ["tag", "search"])("t", "s")
    max_search = 10

    def __init__(self, content):
        self.line = 0

        self.title2id = {}
        self.entries = {}
        self.maxlen_id=0
        self.maxlen_title=0

        for entry in content.entries:
            ent = Entry(entry)
            self.entries[ent.ID.lower()] = ent
            self.title2id[ent.title.lower()] = ent.ID
            if len(ent.ID) > self.maxlen_id: self.maxlen_id = len(ent.ID)
            if len(ent.title) > self.maxlen_title: self.maxlen_title = len(ent.title)

        self.visual = Visualizer()

    def tag(self, arg=None):
        if arg is None:
            tag = self.visual.input("Tag:")
        self.visual.print("got tag: {}".format(tag))
        try:
            for ent in self.entries.values:
                if not ent.has_keywords() or not ent.has_keyword(tag):
                    continue
                self.visual.print("[{}] {}".format(ent.ID, " ".join(ent.keywords)))
        except Exception as x:
            print(x)

    def search(self, query=None):
        if query is None:
            query = self.visual.input("Search:").lower()
        self.visual.print("Got query: {}".format(query))

        # search ids
        res = self.visual.search(query.lower(), [x.lower() for x in self.entries.keys()], self.max_search * 2)
        res = [x + ("id",) for x in res]
        # search titles
        title_res = self.visual.search(query.lower(), [x.title.lower() for x in self.entries.values()], self.max_search * 2)
        # filter to ids
        for t in title_res:
            match_id = self.title2id[t[0]].lower()
            if match_id in [x[0] for x in res]:
                # just add match label
                for r, x in enumerate(res):
                    if x[0] == match_id:
                        res[r] = (x[0], x[1], x[2] + ",title")
                continue
            res.append((match_id, t[1], "title"))
            # sort by score, prune to max
            res = sorted(res, key=lambda obj : obj[1], reverse=True)[:self.max_search]

        for idx, (ID, score, match_by) in enumerate(res):
            idstr = "{:<{w}s}".format("\cite{" + ID + "}", w=self.maxlen_id+7)
            titlestr = "{:<{w}s}".format(self.entries[ID].title, w=self.maxlen_title)
            num_str = "[{:<{w}d}]".format(idx+1, w=len(str(self.max_search)))
            self.visual.print("{}: {}  title: {} match-by: {} | id score: {} ".format(num_str, idstr, titlestr, match_by, score))
        self.visual.newline()


    def check_dual_input(self, command):
        try:
            parts = command.split(maxsplit=1)
            if len(parts) == 0:
                return parts, None
            return parts
        except ValueError:
            return command, None


    def loop(self):
        while(True):
            self.visual.idle()
            command = self.visual.input()
            # check for dual input
            command, arg = self.check_dual_input(command)
            if command == self.commands.tag:
                self.tag(arg)
            elif command == self.commands.search:
                self.search(arg)
