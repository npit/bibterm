import json
from collections import namedtuple, OrderedDict
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

    visual = None

    def __init__(self, kv):
        for key in kv:
            self.__setattr__(key, kv[key])
        self.raw_dict = kv
    def has_keywords(self):
        return self.keywords is not None
    def has_keyword(self, kw):
        if not self.has_keywords():
            return False
        return kw in self.keywords
    def get_pretty_dict(self):
        d=OrderedDict()
        for key in ["ENTRYTYPE", "ID", "author", "title", "year"]:
            if key in self.raw_dict:
                d[key] = self.raw_dict[key]
        return d


# base class to get and print stuff
class Visualizer:
    def idle(self):
        print("Give command: ", end="")

    def list(self, content):
        pass

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

    def input(self, msg=""):
        return input(msg)

    def search(self, query, candidates, atmost):
        return process.extract(query, candidates, limit=atmost)

    def newline(self):
        print()


class Runner:

    max_search = 10

    def __init__(self, content, conf):
        self.line = 0
        self.title2id = {}
        self.entries = {}
        self.maxlen_id = 0
        self.maxlen_title = 0
        self.id_list = []

        for entry in content.entries:
            ent = Entry(entry)
            self.entries[ent.ID.lower()] = ent
            self.title2id[ent.title.lower()] = ent.ID
            if len(ent.ID) > self.maxlen_id:
                self.maxlen_id = len(ent.ID)
            if len(ent.title) > self.maxlen_title:
                self.maxlen_title = len(ent.title)
            self.id_list.append(ent.ID.lower())

        self.visual = Visualizer()
        Entry.visual = self.visual
        self.has_stored_input = False

        # commands = namedtuple("commands", ["tag", "search", "list"])("t", "s", "l")
        ctrl_keys = conf["controls"].keys()
        self.commands = namedtuple("commands",  ctrl_keys) (*[conf["controls"][k] for k in ctrl_keys])

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
            query = self.visual.input("Search:")
        query = query.lower()
        self.visual.print("Got query: {}".format(query))

        # search ids
        res = self.visual.search(query, [x.lower() for x in self.entries.keys()], self.max_search * 2)
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

        id_list = []
        for idx, (ID, score, match_by) in enumerate(res):
            idstr = self.ID_str(ID)
            titlestr = self.title_str(self.entries[ID].title)
            num_str = self.num_str(idx+1, self.max_search)
            self.visual.print("{}: {}  title: {} match-by: {} | id score: {} ".format(num_str, idstr, titlestr, match_by, score))
            id_list.append(ID)
        self.visual.newline()
        while self.select_from_results(id_list):
            pass

    # print entry, only fields of interest
    def inspect_entry(self, thelist, ones_idx):
        if not isinstance(ones_idx, int) or ones_idx > len(thelist) or ones_idx < 1:
            self.visual.print("Invalid index: [{}], enter {} <= idx <= {}".format(ones_idx, 1, len(thelist)))
            return
        ID = thelist[ones_idx-1]
        self.visual.print(json.dumps(self.entries[ID].get_pretty_dict(), indent=2))

    def select_from_results(self, id_list):
        try:
            inp = self.visual.input("Inspect [num] or give new command: ")
            num = int(inp)
            # it's a number, select from results (0-addressable)
            self.inspect_entry(id_list, num)
            return True
        except ValueError:
            # not a number, store input to process in next loop
            self.has_stored_input = True
            self.stored_input = inp
            return False

    def get_stored_input(self):
        self.has_stored_input = False
        return self.stored_input

    def title_str(self, title):
        return "{:<{w}s}".format(title, w=self.maxlen_title)

    def ID_str(self, ID):
        return  "{:<{w}s}".format("\cite{" + ID + "}", w=self.maxlen_id+7)

    def num_str(self, num, maxnum):
        numpad = len(str(maxnum)) - len(str(num))
        return "[{}]{}".format(num, " "*numpad)

    def list(self, arg=None):
        for i, ID in enumerate(self.id_list):
            self.visual.print("{} {} {}".format(
                self.num_str(i+1, len(self.entries)), self.ID_str(ID), self.title_str(self.entries[ID].title)))
        self.visual.newline()
        while self.select_from_results(self.id_list):
            pass

    def check_dual_input(self, command):
        try:
            parts = command.split(maxsplit=1)
            if len(parts) == 0:
                return parts, None
            return parts[0], parts[1:]
        except ValueError:
            return command, None


    def matches(self, cmd, candidate):
        return cmd == candidate or cmd.startswith(candidate)

    def loop(self):
        previous_command = None
        while(True):
            # begin loop
            if not self.has_stored_input:
                self.visual.idle()
                user_input = self.visual.input()
            else:
                user_input = self.get_stored_input()
            # check for dual input
            command, arg = self.check_dual_input(user_input)

            # check for repeat-command
            if command == self.commands.repeat:
                if previous_command is None:
                    self.visual.print("This is the first command.")
                    continue
                command = previous_command

            if command == self.commands.tag:
                self.tag(arg)

            elif self.matches(command, self.commands.search):
                # concat to a single query
                arg = " ".join(arg)
                if command != self.commands.search:
                    arg = str(command[len(self.commands.search):]) + " " + arg
                self.search(arg)
            elif command == self.commands.list:
                self.list(arg)
            else:
                print("Undefined command:", command)
                print("Available:", self.commands)
                return
            previous_command = command

