from collections import namedtuple
from reader import Reader
from visual import setup
# do not use curses, try
#     http: // urwid.org / tutorial /
#     or
#     https: // pypi.org / project / blessings /


class Runner:

    max_search = 10

    def __init__(self, conf, entry_collection=None):
        # setup visual
        self.conf = conf
        self.visual = setup(conf)

        # read the bib database
        if entry_collection is None:
            rdr = Reader(conf)
            rdr.read()
            self.entry_collection = rdr.get_entry_collection()
        else:
            self.entry_collection = entry_collection

        self.has_stored_input = False

        ctrl_keys = conf.controls.keys()
        self.commands = namedtuple("commands", ctrl_keys)(*[conf.controls[k] for k in ctrl_keys])

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
            res = sorted(res, key=lambda obj: obj[1], reverse=True)[:self.max_search]

        id_list = [r[0] for r in res]
        self.visual.print_entries_enum([self.entry_collection.entries[ID] for ID in id_list], self.entry_collection)
        # self.visual.newline()
        while self.select_from_results(id_list):
            pass

    # print entry, only fields of interest
    def inspect_entry(self, thelist, ones_idx):
        if not isinstance(ones_idx, int) or ones_idx > len(thelist) or ones_idx < 1:
            self.visual.print("Invalid index: [{}], enter {} <= idx <= {}".format(ones_idx, 1, len(thelist)))
            return
        ID = thelist[ones_idx - 1]
        self.visual.print_entry_contents(self.entry_collection.entries[ID])

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
        self.visual.print_entries_enum(self.entry_collection.entries.values(), self.entry_collection)
        # self.visual.newline()
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

    def loop(self, input_cmd=None):
        previous_command = None
        while(True):
            # begin loop
            if input_cmd is not None:
                user_input = input_cmd
                input_cmd = None
            elif not self.has_stored_input:
                self.visual.idle()
                user_input = self.visual.input()
            else:
                user_input = self.get_stored_input()
            if not user_input:
                # self.visual.newline()
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
