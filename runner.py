from collections import namedtuple
from reader import Reader
from getter import Getter
from visual import setup
import utils
from editor import Editor
import clipboard
# do not use curses, try
#     http: // urwid.org / tutorial /
#     or
#     https: // pypi.org / project / blessings /


class Runner:

    max_search = None
    max_list = None

    def __init__(self, conf, entry_collection=None):
        # assignments
        self.conf = conf
        self.visual = setup(conf)
        self.editor = None
        self.cached_selection = None
        self.has_stored_input = False

        # maxes list
        self.max_list = 30
        self.max_search = 10

        # read the bib database
        if entry_collection is None:
            rdr = Reader(conf)
            rdr.read()
            self.entry_collection = rdr.get_entry_collection()
        else:
            self.entry_collection = entry_collection


        # map commands
        ctrl_keys = conf.controls.keys()
        self.commands = namedtuple("controls", ctrl_keys)(*[conf.controls[k] for k in ctrl_keys])

        # search settings
        self.searchable_fields = ["ID", "title"]
        self.multivalue_keys = ["author", "keywords"]
        self.searchable_fields += self.multivalue_keys

        # history
        # the entry collection on which commands are executed -- initialized as the whole collection
        self.reference_entry_list = self.entry_collection.id_list
        self.reference_history = [self.entry_collection.id_list]
        self.command_history = [(len(self.entry_collection.id_list), "<start>")]
        self.reference_history_index = 0

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
                self.visual.print_entries_enum([self.entry_collection.entries[ID] for ID in ids], self.entry_collection, additional_fields=list(map(str, scores)), print_newline=True)

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
        self.push_reference_list(results_ids, command="{} {}".format(self.commands.search, query))
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
        return self.entry_collection.modified_collection

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
                at_most = int(arg)
                if at_most >= len(self.reference_entry_list):
                    self.visual.print("Reference is already {}-long.".format(len(self.reference_entry_list)))
                    return
                show_list = self.reference_entry_list[:int(arg)]
            else:
                self.visual.error("Undefined list argument: {}".format(arg))
        self.visual.print_entries_enum([self.entry_collection.entries[x] for x in show_list], self.entry_collection, at_most=self.max_list)
        if len(show_list) < len(self.reference_entry_list):
            self.push_reference_list(show_list, command="{} {}".format(self.commands.list, len(show_list)))
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

    def jump_history(self, index):
        if self.reference_history_index == index:
            self.visual.print("Already here, m8.")
            return
        if index >= 0 and index < len(self.reference_history):
            self.step_history(-self.reference_history_index + index)
        else:
            self.visual.error("Need an index in [1, {}]".format(len(self.reference_history)))


    # move the reference list wrt stored history
    def step_history(self, n_steps):
        self.visual.debug("Stepping through a {}-long history, current index: {}, current length: {}, step is {}".format(len(self.reference_history), self.reference_history_index, len(self.reference_entry_list), n_steps))
        if n_steps > 0:
            if self.reference_history_index + n_steps > len(self.reference_history) - 1:
                self.visual.error("History length: {} current index: {} attempted step stride: {}.".format(len(self.reference_history), self.reference_history_index, n_steps))
                return
            switch_msg = "forward"
        else:
            if self.reference_history_index + n_steps < 0:
                self.visual.error("History length: {} current index: {} attempted step stride: {}.".format(len(self.reference_history), self.reference_history_index, n_steps))
                return
            switch_msg = "backwards"
        self.reference_history_index += n_steps
        self.reference_entry_list = self.reference_history[self.reference_history_index]
        self.visual.print("Switched {} to {}-long reference list.".format(switch_msg, len(self.reference_entry_list)))
        self.list()

    def show_history(self):
        current_mark = ["" for _ in self.command_history]
        current_mark[self.reference_history_index] = "*"
        self.visual.print_enum(self.command_history, additionals=current_mark)
        self.visual.debug("History length: {}, history lengths: {}, current index: {}, current length: {}.".format(len(self.reference_history),[len(x) for x in self.reference_history], self.reference_history_index, len(self.reference_entry_list)))

    # add to reference list history
    def push_reference_list(self, new_list, command):
        # register the new reference
        if new_list == self.reference_entry_list:
            return
        self.reference_history.append(new_list)
        self.reference_history_index += 1
        self.reference_entry_list = new_list
        self.visual.print("Switching to new {}-long reference list.".format(len(self.reference_entry_list)))

        # store the command that produced it
        self.command_history.append((len(self.reference_entry_list), command))


    def get_input(self, input_cmd):
        if input_cmd is not None:
            user_input = input_cmd
            self.visual.debug("Got input from main: [{}]".format(input_cmd))
            input_cmd = None
        elif not self.has_stored_input:
            self.visual.idle()
            user_input = self.visual.input()
        else:
            user_input = self.get_stored_input()
        return user_input, input_cmd

    def get_index_selection(self, inp):
        if not inp:
            if self.cached_selection is not None:
                return self.cached_selection
            # no input provided
            return []
        else:
            nums = utils.get_index_list(inp)
            if utils.has_none(nums):
                # non numeric input
                return None
            return nums

    def loop(self, input_cmd=None):
        previous_command = None
        while(True):
            # begin loop
            user_input, input_cmd = self.get_input(input_cmd)
            if not user_input:
                # self.visual.newline()
                continue

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

            if command == self.commands.history_back:
                n_steps = utils.str_to_int(arg, default=-1)
                self.step_history(n_steps)
            elif command == self.commands.history_forward:
                n_steps = utils.str_to_int(arg, default=1)
                self.step_history(n_steps)
            elif command == self.commands.history_jump:
                idx = utils.str_to_int(arg)
                if idx is None:
                    self.visual.error("Need history index to jump to.")
                    continue
                self.jump_history(idx - 1)
            elif command == self.commands.history_show:
                self.show_history()
            elif utils.matches(command, self.commands.cite):
                nums = self.get_index_selection(arg)
                if nums is None or not nums:
                    self.visual.error("Need a selection to cite.")
                    continue
                citation = "\\cite{{{}}}".format(", ".join([self.reference_entry_list[n-1] for n in nums]))
                clipboard.copy(citation)
                self.visual.print("Copied to clipboard: {}".format(citation))
            elif command.startswith(self.commands.pdf_file):
                nums = self.get_index_selection(arg)
                if nums is None or not nums:
                    self.visual.error("Need a selection to cite.")
                    continue
                for n in nums:
                    entry = self.entry_collection.entries[self.reference_entry_list[n-1]]
                    updated_entry = self.get_editor().set_file(entry)
                    if self.editor.collection_modified and updated_entry is not None:
                        self.entry_collection.replace(updated_entry)
            elif command.startswith(self.commands.search):
                query = arg if arg else ""
                # concat to a single query
                if command != self.commands.search:
                    query = str(command[len(self.commands.search):]) + query
                if not query:
                    self.visual.error("Search what?")
                    continue
                self.search(query.lower().strip())
            elif utils.matches(command, self.commands.list):
                self.list(arg)
            elif utils.matches(command, self.commands.tag):
                nums = self.get_index_selection(arg)
                if nums is None or not nums:
                    self.visual.error("Need a selection to cite.")
                    continue
                for num in nums:
                    entry = self.entry_collection.entries[self.reference_entry_list[num - 1]]
                    updated_entry = self.get_editor().tag(entry)
                    if self.editor.collection_modified and updated_entry is not None:
                        self.entry_collection.replace(updated_entry)
                self.editor.clear_cache()
            elif utils.matches(command, "open"):
                # arg has to be a single string
                nums = self.get_index_selection(arg)
                if utils.has_none(nums):
                    self.visual.print("Need a valid entry index.")
                for num in nums:
                    self.get_editor().open(self.entry_collection.entries[self.reference_entry_list[num - 1]])
            elif utils.matches(command, "get"):
                getter = Getter(self.conf)
                res = getter.get(arg)
                reader2 = Reader(self.conf)
                reader2.read_string(res)
                self.visual.print("Got entry item(s):")
                for entry in reader2.get_entry_collection().entries.values():
                    self.visual.print_entry_contents(entry)
                what = self.visual.input("Store?", "*yes no")
                if utils.matches(what, "no"):
                    continue
                for entry in reader2.get_entry_collection().entries.values():
                    self.entry_collection.create(entry)

            elif command[0].isdigit():
                # print(self.reference_entry_list)
                # for numeric input, select these entries
                self.select(user_input)
            else:
                self.visual.error("Undefined command: {}".format(command))
                self.visual.print("Available: {}".format(self.commands))
            previous_command = command
