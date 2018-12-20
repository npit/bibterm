from collections import namedtuple
from reader import Reader
from visual import setup
import utils
from editor import Editor
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
        self.editor = None
        self.cached_selection = None

        # read the bib database
        if entry_collection is None:
            rdr = Reader(conf)
            rdr.read()
            self.entry_collection = rdr.get_entry_collection()
        else:
            self.entry_collection = entry_collection

        self.has_stored_input = False

        # map commands
        ctrl_keys = conf.controls.keys()
        self.commands = namedtuple("controls", ctrl_keys)(*[conf.controls[k] for k in ctrl_keys])
        list_ctrl_keys = conf.list_controls.keys()
        self.edit_commands = namedtuple("list_controls", list_ctrl_keys)(*[conf.list_controls[k] for k in list_ctrl_keys])

        self.searchable_fields = ["ID", "title"]
        self.multivalue_keys = ["author", "keywords"]
        self.searchable_fields += self.multivalue_keys

        # the entry collection on which commands are executed -- initialized as the whole collection
        self.reference_entry_list = self.entry_collection.id_list
        self.reference_history = []

    def search(self, query=None):
        if query is None:
            query = self.visual.input("Search:")
        query = query.lower()
        self.visual.print("Got query: {}".format(query))
        results_ids, match_scores = [], []
        # search all searchable fields
        for field in self.searchable_fields:
            res = self.filter(field, query)
            ids, scores = [r[0] for r in res], [r[1] for r in res]
            with utils.OnlyDebug(self.visual):
                self.visual.print("Results for query: {} on field: {}".format(query, field))
                self.visual.print_entries_enum([self.entry_collection.entries[ID] for ID in ids], self.entry_collection, additional_fields=scores, print_newline=True)

            for i in range(len(ids)):
                if ids[i] in results_ids:
                    existing_idx = results_ids.index(ids[i])
                    # replace score, if it's higher
                    if scores[i] > match_scores[existing_idx]:
                        match_scores[existing_idx] = scores[i]
                else:
                    # if not there, just append
                    results_ids.append(ids[i])
                    match_scores.append(scores[i])

        results_ids = sorted(zip(results_ids, match_scores), key=lambda x: x[1], reverse=True)
        results_ids, match_scores = [r[0] for r in results_ids], [r[1] for r in results_ids]

        self.visual.print_entries_enum([self.entry_collection.entries[ID] for ID in results_ids], self.entry_collection)
        self.push_reference_list(results_ids)
        # while self.select_from_results(results_ids):
        #     pass

    # print entry, only fields of interest
    def inspect_entry(self, ones_idx):
        if not isinstance(ones_idx, int) or ones_idx > len(self.reference_entry_list) or ones_idx < 1:
            self.visual.print("Invalid index: [{}], enter {} <= idx <= {}".format(ones_idx, 1, len(self.reference_entry_list)))
            return
        ID = self.reference_entry_list[ones_idx - 1]
        self.visual.print_entry_contents(self.entry_collection.entries[ID])

    # singleton editor fetcher
    def get_editor(self):
        if self.editor is None:
            self.editor = Editor(self.conf)
        return self.editor

    def string_to_entry_num(self, num_str):
        try:
            num = int(num_str)
            if not self.entry_collection.num_in_range(num):
                self.visual.print("{} is outside of entry number range: [1,{}] .".format(num, len(self.entry_collection.id_list)))
                return None
            return num
        except ValueError:
            self.visual.print("Whoopsie, sth went wrong.")
            return None

    def modified_collection(self):
        if self.editor is None:
            return False
        return self.editor.collection_modified

    def select(self, inp):
            # no command offered: it's a number, select from results (0-addressable)
            nums = utils.get_index_list(inp)
            for num in nums:
                self.inspect_entry(num)
            self.cached_selection = nums

    def get_stored_input(self):
        self.has_stored_input = False
        return self.stored_input

    def list(self, arg=None):
        show_list = self.reference_entry_list
        if arg is not None and arg:
            if arg[0].isdigit():
                show_list = self.reference_entry_list[:int(arg)]
            else:
                self.visual.error("Undefined list argument: {}".format(arg))
        self.visual.print_entries_enum([self.entry_collection.entries[x] for x in show_list], self.entry_collection)
        if len(show_list) < len(self.reference_entry_list):
            self.push_reference_list(show_list)
        # self.visual.newline()
        # while self.select_from_results(self.entry_collection.id_list):
        #     pass

    def is_multivalue_key(self, filter_key):
        return filter_key in self.multivalue_keys

    # show entries matching a filter
    def filter(self, filter_key, filter_value, max_search=None):
        if max_search is None:
            max_search = self.max_search
        if filter_key not in self.searchable_fields:
            self.visual.warn("Must filter with a key in: {}".format(self.searchable_fields))
            return
        candidate_values = []
        searched_entry_ids = []
        # get candidate values, as key to a value: entry_id dict
        for x in self.reference_entry_list:
            entry = self.entry_collection.entries[x]
            value = getattr(entry, filter_key)
            if type(value) == str:
                value = value.lower()
            else:
                if value is None:
                    continue

            searched_entry_ids.append(x)
            candidate_values.append(value)

        # search and return ids of results
        res = self.visual.search(filter_value, candidate_values, max_search, self.is_multivalue_key(filter_key))
        if filter_key == "ID":
            # return the IDs
            return [r[0] for r in res]
        elif filter_key == "title":
            return [(self.entry_collection.title2id[r[0][0]], r[0][1]) for r in res]
        elif self.is_multivalue_key(filter_key):
            # limit results per keyword
            res = [(searched_entry_ids[r[1]], r[0][1]) for r in res]
        return res

    # checks wether command and arguments are inserted at once
    def check_dual_input(self, command):
        parts = command.split(maxsplit=1)
        cmd = parts[0]
        if len(parts) == 1:
            arg = None
        else:
            arg = parts[1]
        return cmd, arg

    def step_back_history(self):
        self.reference_entry_list = self.reference_history.pop()
        self.visual.print("Switching back to {}-long reference list.".format(len(self.reference_entry_list)))
        self.list()

    # add to reference list history
    def push_reference_list(self, new_list):
        if new_list == self.reference_entry_list:
            return
        self.reference_history.append(self.reference_entry_list)
        self.reference_entry_list = new_list
        self.visual.print("Switching to new {}-long reference list.".format(len(self.reference_entry_list)))

    def loop(self, input_cmd=None):
        previous_command = None
        while(True):
            # begin loop
            if input_cmd is not None:
                user_input = input_cmd
                self.visual.debug("Got input from main: [{}]".format(input_cmd))
                input_cmd = None
            elif not self.has_stored_input:
                self.visual.idle()
                user_input = self.visual.input()
            else:
                user_input = self.get_stored_input()
            if not user_input:
                # self.visual.newline()
                continue

            print(user_input)
            # check for dual input
            command, arg = self.check_dual_input(user_input)
            self.visual.debug("Command: [{}] , arg: [{}]".format(command, arg))

            # check for repeat-command
            if command == self.commands.repeat:
                if previous_command is None:
                    self.visual.print("This is the first command.")
                    continue
                command = previous_command

            if command == self.commands.quit:
                break

            if command.startswith(self.commands.search):
                # concat to a single query
                if command != self.commands.search:
                    query = str(command[len(self.commands.search):])
                    if arg:
                        query += " " + arg
                self.search(query.lower().strip())
            elif utils.matches(command, self.commands.list):
                self.list(arg)
            elif utils.matches(command, self.commands.tag):
                print(self.reference_entry_list)
                # arg has to be a single string
                if not arg:
                    if self.cached_selection is not None:
                        nums = self.cached_selection
                    else:
                        self.visual.error("Need an entry argument to tag.")
                        continue
                else:
                    nums = utils.get_index_list(arg)
                    if any([x is None for x in nums]) or not nums:
                        self.visual.print("Need a valid entry index.")
                        continue
                for num in nums:
                    entry = self.entry_collection.entries[self.reference_entry_list[num - 1]]
                    updated_entry = self.get_editor().tag(entry)
                    if self.editor.collection_modified and updated_entry is not None:
                        self.entry_collection.replace(updated_entry)
                self.editor.clear_cache()

            elif utils.matches(command, "open"):
                # arg has to be a single string
                if not arg:
                    if self.cached_selection is not None:
                        nums = self.cached_selection
                    else:
                        self.visual.error("Need an entry argument to open.")
                        continue
                else:
                    nums = utils.get_index_list(arg)
                    if any([x is None for x in nums]) or not nums:
                        self.visual.print("Need a valid entry index.")
                for num in nums:
                    self.get_editor().open(self.entry_collection.entries[self.reference_entry_list[num - 1]])
                return True
            elif command[0].isdigit():
                print(self.reference_entry_list)
                # for numeric input, select these entries
                self.select(user_input)
            else:
                self.visual.error("Undefined command:", command)
                self.visual.print("Available:", self.commands)
                continue
            previous_command = command
