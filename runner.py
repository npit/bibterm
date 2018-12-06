import json
from collections import namedtuple, OrderedDict
from reader import Reader
from visual import setup
# do not use curses, try
#     http: // urwid.org / tutorial /
#     or
#     https: // pypi.org / project / blessings /

def loop(runner):
    runner.loop()

class EntryCollection:
    def __init__(self, bib_db):
        self.bibtex_db = bib_db
        self.title2id = {}
        self.entries = {}
        self.maxlen_id = 0
        self.maxlen_title = 0
        self.id_list = []
        self.title_list = []
        for entry in bib_db.entries:
            ent = Entry(entry)
            self.insert(ent)

    def only_keep(self, keep_ids):
        for ID in self.id_list:
            if ID in keep_ids:
                continue
            title = self.entries[ID].title.lower()
            self.id_list.remove(ID)
            del self.entries[ID]
            self.title_list.remove(title)
            del self.title2id[title]

    def insert_new(self, ent):
        self.insert(ent)
        # update underlying bibtex database
        self.bibtex_db.entries.append(ent.raw_dict)
        self.bibtex_db.entries_dict[ent.ID] = ent.raw_dict

    def insert(self, ent):
        ID = ent.ID.lower()
        title = ent.title.lower()
        # update object lookup dict
        self.entries[ID] = ent
        # update title-id mapping
        self.title2id[title] = ent.ID.lower()
        # update ids and titles lists
        self.id_list.append(ID)
        self.title_list.append(title)
        # update maximum ID / title lengths
        if len(ent.ID) > self.maxlen_id:
            self.maxlen_id = len(ent.ID)
        if len(ent.title) > self.maxlen_title:
            self.maxlen_title = len(ent.title)

    def get_writable_db(self):
        stringify_keys = ["author", "keywords", "journal", "link"]
        for key in stringify_keys:
            for i in range(len(self.bibtex_db.entries)):
                print(self.bibtex_db.entries[i]["ID"])
                if key not in self.bibtex_db.entries[i]:
                    continue
                print(key, self.bibtex_db.entries[i][key])
                if type(self.bibtex_db.entries[i][key]) != str:
                    self.bibtex_db.entries[i][key] = ", ".join(self.bibtex_db.entries[i][key])
            for ID in self.bibtex_db.entries_dict:
                print(ID)
                if key not in self.bibtex_db.entries_dict[ID]:
                    continue
                print(key, self.bibtex_db.entries_dict[ID][key])
                if type(self.bibtex_db.entries_dict[ID][key]) != str:
                    self.bibtex_db.entries_dict[ID][key] = ", ".join(self.bibtex_db.entries_dict[ID][key])
        return self.bibtex_db
    






    
            
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



class Runner:

    max_search = 10

    def __init__(self, conf, entry_collection=None):
        # read the bib database
        if entry_collection is None:
            rdr = Reader(conf)
            rdr.read()
            self.entry_collection = EntryCollection(rdr.get_content().entries)
        else:
            self.entry_collection = entry_collection

        self.visual = setup(conf)

        Entry.visual = self.visual
        self.has_stored_input = False

        # commands = namedtuple("commands", ["tag", "search", "list"])("t", "s", "l")
        ctrl_keys = conf.controls.keys()
        self.commands = namedtuple("commands",  ctrl_keys) (*[conf.controls[k] for k in ctrl_keys])

    def tag(self, arg=None):
        if arg is None:
            tag = self.visual.input("Tag:")
        self.visual.print("got tag: {}".format(tag))
        try:
            for ent in self.entry_collection.entries.values:
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
        res = self.visual.search(query, [x.lower() for x in self.entry_collection.entries.keys()], self.max_search * 2)
        res = [x + ("id",) for x in res]
        # search titles
        title_res = self.visual.search(query.lower(), [x.title.lower() for x in self.entry_collection.entries.values()], self.max_search * 2)
        # filter to ids
        for t in title_res:
            match_id = self.entry_collection.title2id[t[0]].lower()
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
            idstr = self.visual.ID_str(ID, self.entry_collection, self.entry_collection)
            titlestr = self.visual.title_str(self.entry_collection.entries[ID].title, self.entry_collection, self.entry_collection)
            num_str = self.visual.num_str(idx+1, self.max_search)
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
        self.visual.print(json.dumps(self.entry_collection.entries[ID].get_pretty_dict(), indent=2))

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

    def list(self, arg=None):
        for i, ID in enumerate(self.entry_collection.id_list):
            self.visual.print("{} {} {}".format(
                self.visual.num_str(i+1, len(self.entry_collection.entries)), self.visual.ID_str(ID, self.entry_collection), self.visual.title_str(self.entry_collection.entries[ID].title, self.entry_collection)))
        self.visual.newline()
        while self.select_from_results(self.entry_collection.id_list):
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
            if not user_input:
                self.visual.newline()
                continue

            # check for dual input
            command, arg = self.check_dual_input(user_input)

            # check for repeat-command
            if command == self.commands.repeat:
                if previous_command is None:
                    self.visual.print("This is the first command.")
                    continue
                command = previous_command

            if command == self.commands.quit:
                break

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
                continue
            previous_command = command

