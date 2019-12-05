from collections import namedtuple

import clipboard

import utils
from editor import Editor
from getters.getter import Getter
from reader import Entry, Reader
from visual import setup

# do not use curses, try
#     http: // urwid.org / tutorial /
#     or
#     https: // pypi.org / project / blessings /


class Runner:

    max_search = None
    max_list = None
    search_invoke_counter = None
    do_update_config = False
    config_update = []

    def __init__(self, conf, entry_collection=None):
        # assignments
        self.conf = conf
        self.editor = None
        self.getter = None
        self.cached_selection = None
        self.has_stored_input = False

        # read the bib database
        if entry_collection is None:
            rdr = Reader(conf)
            rdr.read()
            self.entry_collection = rdr.get_entry_collection()
        else:
            self.entry_collection = entry_collection

        # map commands
        ctrl_keys = conf.controls.keys()
        self.commands_dict = conf.controls
        self.commands = namedtuple("controls", ctrl_keys)(*[conf.controls[k] for k in ctrl_keys])

        # search settings
        self.searchable_fields = ["ID", "title"]
        self.multivalue_keys = ["author", "keywords"]
        self.searchable_fields += self.multivalue_keys

        # history
        self.reset_history()

        # ui
        self.visual = setup(conf)

        # maxes list
        # delegate handling of maximum results number to the visual component or not
        if self.visual.handles_max_results:
            self.max_list = 30
            self.max_search = 10
        else:
            self.max_list = None
            self.max_search = None
        self.search_invoke_counter = 0

    def search(self, query=None):
        self.visual.log("Starting search")
        if self.search_invoke_counter > 0:
            # step to the starting history to search everything
            self.reset_history()
        search_done = False
        just_began_search = True
        query_supplied = bool(query)
        while True:
            # get new search object, if it's a continued search OR no pre-given query
            if not just_began_search or (just_began_search and not query_supplied):
                search_done, new_query = self.visual.receive_search()
                if search_done is None:
                    self.visual.message("Aborting search")
                    return
                if new_query == "" and search_done:
                    # pressed enter
                    break
                query = new_query
            query = query.lower().strip()
            self.visual.log("Got query: {}".format(query))
            results_ids, match_scores = [], []
            # search all searchable fields
            for field in self.searchable_fields:
                res = self.filter(field, query)
                ids, scores = [r[0] for r in res], [r[1] for r in res]
                with utils.OnlyDebug(self.visual):
                    self.visual.debug("Results for query: {} on field: {}".format(query, field))
                    self.visual.print_entries_enum([self.entry_collection.entries[ID] for ID in ids],
                                                   self.entry_collection, additional_fields=list(map(str, scores)),
                                                   print_newline=True)

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
            # apply max search results filtering
            results_ids = results_ids[:self.max_search]
            results_ids, match_scores = [r[0] for r in results_ids], [r[1] for r in results_ids]

            self.visual.print_entries_enum([self.entry_collection.entries[ID] for ID in results_ids], self.entry_collection)
            just_began_search = False
            self.search_invoke_counter += 1
            if not self.visual.does_incremental_search:
                break
        # push the reflist modification to history
        self.change_history(results_ids, "search:\"{}\"".format(query))

    # print entry, only fields of interest
    def inspect_entries(self, ones_idxs):
        for ones_idx in ones_idxs:
            if not isinstance(ones_idx, int) or ones_idx > len(self.reference_entry_id_list) or ones_idx < 1:
                self.visual.error("Invalid index: [{}], enter {} <= idx <= {}".format(ones_idx, 1, len(self.reference_entry_id_list)))
                return

        ids = [self.reference_entry_id_list[ones_idx - 1] for ones_idx in ones_idxs]
        # self.visual.print("Entry #[{}]".format(ones_idx))
        self.visual.print_entries_contents([self.entry_collection.entries[ID] for ID in ids])
        # self.visual.print_entry_contents(self.entry_collection.entries[ID])

    # singleton getter fetcher
    def get_getter(self):
        if self.getter is None:
            self.getter = Getter(self.conf)
        return self.getter

    def accumulate_config_updates(self):
        if self.getter is not None:
            if self.getter.do_update_config:
                self.do_update_config = True
                self.config_update.append(self.getter.get_config_update())

    def get_config_update(self):
        return self.config_update

    # singleton editor fetcher
    def get_editor(self):
        if self.editor is None:
            self.editor = Editor(self.conf)
        return self.editor

    def string_to_entry_num(self, num_str):
        try:
            num = int(num_str)
            if not self.entry_collection.num_in_range(num):
                self.visual.error("{} is outside of entry number range: [1,{}] .".format(num, len(self.entry_collection.id_list)))
                return None
            return num
        except ValueError:
            self.visual.error("Whoopsie, sth went wrong.")
            return None

    def modified_collection(self):
        return self.entry_collection.modified_collection

    def unselect(self):
        self.cached_selection = None

    def select(self, inp):
        # no command offered: it's a number, select from results (0-addressable)
        nums = utils.get_index_list(inp, len(self.reference_entry_id_list))
        if nums is None:
            self.visual.log("Invalid selection: {}".format(inp))
            return
        self.visual.log("Displaying {} {}: {}".format(len(nums), "entry" if len(nums) == 1 else "entries", nums))
        self.inspect_entries(nums)
        self.cached_selection = nums

    def get_stored_input(self):
        self.has_stored_input = False
        return self.stored_input

    def list(self, arg=None):
        show_list = self.reference_entry_id_list
        nums = self.get_index_selection(arg)
        if nums:
            show_list = [self.reference_entry_id_list[n - 1] for n in nums]
            if show_list != self.reference_entry_id_list:
                # push the history change
                self.change_history(show_list, "{} {}".format(self.commands.list, len(show_list)))
        else:
            show_list = self.reference_entry_id_list
        self.visual.print_entries_enum([self.entry_collection.entries[x] for x in show_list], self.entry_collection, at_most=self.max_list)

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
        for x in self.reference_entry_id_list:
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
        if not command:
            return "", None
        parts = command.split(maxsplit=1)
        cmd = parts[0]
        if len(parts) == 1:
            arg = None
        else:
            arg = parts[1]
        return cmd, arg

    def jump_history(self, index):
        if self.reference_history_index == index:
            self.visual.error("Already on starting history.")
            return
        if index >= 0 and index < len(self.reference_history):
            self.step_history(-self.reference_history_index + index)
        else:
            self.visual.error("Need an index in [1, {}]".format(len(self.reference_history)))

    def reset_history(self):
        # the entry collection on which commands are executed -- initialized as the whole collection
        self.reference_entry_id_list = self.entry_collection.id_list
        self.reference_history = [self.entry_collection.id_list]
        self.command_history = [(len(self.entry_collection.id_list), "<start>")]
        self.reference_history_index = 0
        self.unselect()

    # move the reference list wrt stored history
    def step_history(self, n_steps):
        self.visual.debug("Stepping through a {}-long history, current index: {}, current length: {}, step is {}".format(len(self.reference_history), self.reference_history_index, len(self.reference_entry_id_list), n_steps))
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
        self.reference_entry_id_list = self.reference_history[self.reference_history_index]
        self.visual.log("Switched {} to {}-long reference list: {}.".format(switch_msg, len(self.reference_entry_id_list), self.command_history[self.reference_history_index]))
        self.list()

    def show_history(self):
        current_mark = ["" for _ in self.command_history]
        current_mark[self.reference_history_index] = "*"
        self.visual.print_enum(self.command_history, additionals=current_mark)
        self.visual.debug("History length: {}, history lengths: {}, current index: {}, current length: {}.".format(len(self.reference_history), [len(x) for x in self.reference_history], self.reference_history_index, len(self.reference_entry_id_list)))

    def change_history(self, new_reflist, modification_msg):
        """Change the reference list to its latest modificdation

        Calling the function after a search or a truncated list, will set the reference list to the resulting entry set.
        """
        self.visual.log("Changed reference list to [{}], with {} items.".format(modification_msg, len(new_reflist)))
        self.push_reference_list(new_reflist, modification_msg)
        # unselect stuff -- it's meaningless now
        self.unselect()

    # add to reference list history
    def push_reference_list(self, new_list, command, force=False):
        # no duplicates
        if new_list == self.reference_entry_id_list and not force:
            return
        # register the new reference
        self.reference_history.append(new_list)
        self.reference_history_index += 1
        self.reference_entry_id_list = new_list
        self.visual.message("Switching to new {}-long reference list.".format(len(self.reference_entry_id_list)))

        # store the command that produced it
        self.command_history.append((len(self.reference_entry_id_list), command))

    def get_input(self, input_cmd):
        self.visual.idle()
        if input_cmd is not None:
            user_input = input_cmd
            self.visual.debug("Got input from main: [{}]".format(input_cmd))
            input_cmd = None
        elif not self.has_stored_input:
            user_input = self.visual.receive_command()
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
            nums = utils.get_index_list(inp, len(self.reference_entry_id_list))
            if utils.has_none(nums):
                # non numeric input
                return None
            invalids = [x for x in nums if x > len(self.reference_entry_id_list)]
            if invalids:
                self.visual.error("Invalid index(es): {}".format(invalids))
            nums = [x for x in nums if x not in invalids]
            self.cached_selection = nums
            return nums

    def save_if_modified(self, verify_write=True, called_explicitely=False):
        # collection
        modified_status = "*has been modified*" if self.modified_collection() else "has not been modified"
        if verify_write:
            # for explicit calls, do not ask for verification
            if called_explicitely:
                pass
            else:
                # if auto-called and not modified, do nothing
                if not self.modified_collection():
                    return
                # else verify
                if not self.visual.yes_no("The collection {}. Overwrite?".format(modified_status), default_yes=False):
                    return
        # write
        self.entry_collection.overwrite_file(self.conf)
        self.entry_collection.reset_modified()
        # config


    def set_local_pdf_path(self, str_selection=None):
        nums = self.get_index_selection(str_selection)
        if nums is None or not nums or len(nums) > 1:
            self.visual.error("Need a single selection to set pdf to.")
            return
        entry = self.entry_collection.entries[self.reference_entry_id_list[nums[0] - 1]]
        if entry.file is not None:
            if not self.visual.yes_no("Pdf attribute exists: {}, replace?".format(entry.file), default_yes=False):
                return
        updated_entry = self.get_editor().set_file(entry)
        if self.editor.collection_modified and updated_entry is not None:
            self.entry_collection.replace(updated_entry)
            self.visual.log("Entry {} updated with pdf path.".format(entry.ID))

    def get_pdf_from_web(self, str_selection=None):
        nums = self.get_index_selection(str_selection)
        if nums is None or not nums or len(nums) > 1:
            self.visual.error("Need a single selection to download pdf to.")
            return
        entry_id = self.reference_entry_id_list[nums[0] - 1]
        entry = self.entry_collection.entries[entry_id]
        if entry.file is not None:
            if not self.visual.yes_no("Pdf attribute exists: {}, replace?".format(entry.file), default_yes=False):
                return
        getter = Getter(self.conf)
        pdf_url = self.visual.ask_user("Give pdf url to download", multichar=True)
        file_path = getter.get_web_pdf(pdf_url, entry_id)
        if file_path is None:
            self.visual.error("Failed to download from {}.".format(pdf_url))
            return
        updated_entry = self.get_editor().set_file(entry, file_path=file_path)
        self.entry_collection.replace(updated_entry)

    def search_web_pdf(self, str_selection=None):
        nums = self.get_index_selection(str_selection)
        if nums is None or not nums or len(nums) > 1:
            self.visual.error("Need a single selection to download pdf to.")
            return
        entry_id = self.reference_entry_id_list[nums[0] - 1]
        entry = self.entry_collection.entries[entry_id]
        if entry.file is not None:
            if not self.visual.yes_no("Pdf attribute exists: {}, replace?".format(entry.file), default_yes=False):
                return
        pdf_path = self.get_getter().search_web_pdf(entry_id, entry.title)
        if not pdf_path:
            self.visual.log("Invalid pdf path, aborting.")
            return
        updated_entry = self.get_editor().set_file(entry, file_path=pdf_path)
        if updated_entry is None:
            return
        self.entry_collection.replace(updated_entry)

    def loop(self, input_cmd=None):
        previous_command = None
        while(True):
            # begin loop
            user_input, input_cmd = self.get_input(input_cmd)
            # check for dual input
            command, arg = self.check_dual_input(user_input)
            self.visual.debug("Command: [{}] , arg: [{}]".format(command, arg))

            # check for repeat-command
            if command == self.commands.repeat:
                if previous_command is None:
                    self.visual.debug("This is the first command.")
                    continue
                command = previous_command
            if command == self.commands.quit:
                break
            # history
            # -------------------------------------------------------
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
            elif command == self.commands.history_reset:
                self.visual.message("Resetting history.")
                self.reset_history()
            elif command == self.commands.history_show:
                self.show_history()
            # -------------------------------------------------------
            elif command == self.commands.delete:
                nums = self.get_index_selection(arg)
                if nums is None or not nums:
                    self.visual.error("Need a selection to delete.")
                    continue
                to_delete = [self.reference_entry_id_list[n - 1] for n in nums]
                old_len, del_len = len(self.reference_entry_id_list), len(to_delete)
                for entry_id in to_delete:
                    self.entry_collection.remove(entry_id)
                    self.visual.log("Deleted entry {}".format(entry_id))
                remaining = [x for x in self.reference_entry_id_list if x not in to_delete]
                self.visual.log("Deleted {}/{} entries, left with {}".format(del_len, old_len, len(remaining)))
                self.push_reference_list(remaining, "deletion", force=True)
                self.do_update_config = True
                self.unselect()

            # latex citing
            elif utils.matches(command, self.commands.cite):
                nums = self.get_index_selection(arg)
                if nums is None or not nums:
                    self.visual.error("Need a selection to cite.")
                    continue
                citation_id = ", ".join([self.reference_entry_id_list[n - 1] for n in nums])
                citation = "\\cite{{{}}}".format(citation_id)
                # clipboard.copy(citation_id)
                clipboard.copy(citation)
                self.visual.message("Copied to clipboard: {}".format(citation))
            # -------------------------------------------------------
            # adding local paths to pdfs
            elif command.startswith(self.commands.pdf_file):
                self.set_local_pdf_path(arg)
            # fetching pdfs from a web URL
            elif command == self.commands.pdf_web:
                self.get_pdf_from_web(arg)
            # searching for a pdf in an external browser
            elif command == self.commands.pdf_search:
                self.search_web_pdf(arg)
            # searching
            elif command.startswith(self.commands.search):
                query = arg if arg else ""
                if command == self.commands.search and not arg:
                    pass
                else:
                    query = str(command[len(self.commands.search):]) + query
                self.search(query)
            # listing
            elif utils.matches(command, self.commands.list):
                self.list(arg)
            # adding tags
            elif utils.matches(command, self.commands.tag):
                nums = self.get_index_selection(arg)
                if nums is None or not nums:
                    self.visual.error("Need a selection to cite.")
                    continue
                for num in nums:
                    entry = self.entry_collection.entries[self.reference_entry_id_list[num - 1]]
                    updated_entry = self.get_editor().tag(entry)
                    if self.editor.collection_modified and updated_entry is not None:
                        self.entry_collection.replace(updated_entry)
                self.editor.clear_cache()
            # opening pdfs
            elif utils.matches(command, self.commands.pdf_open):
                nums = self.get_index_selection(arg)
                if not nums or nums is None:
                    self.visual.print("Need a selection to open.")
                # arg has to be a single string
                nums = self.get_index_selection(arg)
                if utils.has_none(nums):
                    self.visual.print("Need a valid entry index.")
                for num in nums:
                    entry_id = self.reference_entry_id_list[num - 1]
                    entry = self.entry_collection.entries[entry_id]
                    pdf_in_entry = self.get_editor().open(entry)
                    if not pdf_in_entry and len(nums) == 1:
                        if self.visual.yes_no("Search for pdf on the web?"):
                            self.search_web_pdf()

            # fetch bibtexs from the web
            elif utils.matches(command, self.commands.get):
                getter = self.get_getter()
                if not arg:
                    arg = self.visual.ask_user("Search what on the web?", multichar=True)
                    if not arg:
                        self.visual.error("Nothing entered, aborting.")
                        continue
                try:
                    res = getter.get_web_bibtex(arg)
                except Exception as ex:
                    self.visual.error("Failed to complete the query: {}.".format(ex))
                    continue
                if not res:
                    self.visual.error("No data retrieved.")
                    continue

                reader2 = Reader(self.conf)
                read_entries_dict = reader2.read_entry_list(res)
                self.visual.log("Retrieved {} entry item(s) from query [{}]".format(len(read_entries_dict), arg))

                # select subset
                if len(read_entries_dict) > 1:
                    ids, content = list(zip(*[(e.ID, e.get_discovery_view()) for e in read_entries_dict.values()]))
                    _, selected_ids = self.visual.user_multifilter(content, header=Entry.discovery_keys, reference=ids)
                    selected_entries = [v for (k, v) in read_entries_dict.items() if k in selected_ids]
                else:
                    selected_entries = list(read_entries_dict.values())


                self.visual.print_entries_contents(selected_entries)
                if not self.visual.yes_no("Store?"):
                    continue
                for entry in selected_entries:
                    created = self.entry_collection.create(entry)
                if not self.visual.yes_no("Select it?"):
                    continue
                if not created:
                    continue
                self.reset_history()
                self.cached_selection = [i + 1 for i in range(len(self.reference_entry_id_list)) if self.reference_entry_id_list[i] in read_entries_dict]
                self.visual.message("Item is now selected: {}.".format(self.cached_selection))

                # pdf
                what = self.visual.ask_user("Pdf?", "local url web-search *skip")
                if utils.matches(what, "skip"):
                    continue
                if utils.matches(what, "url"):
                    self.get_pdf_from_web()
                    continue
                if utils.matches(what, "local"):
                    self.set_local_pdf_path()
                    continue
                if utils.matches(what, "web-search"):
                    self.search_web_pdf()

            # save collection
            elif utils.matches(command, self.commands.save):
                self.save_if_modified(called_explicitely=True)
                continue
            elif command == self.commands.clear:
                self.visual.clear()
            elif command == self.commands.unselect:
                self.cached_selection = None
            elif command == self.commands.show:
                if self.cached_selection is not None:
                    self.select(self.cached_selection)
                else:
                    self.visual.error("No selection to show.")
            elif command == self.commands.up:
                self.visual.up()
            elif command == self.commands.down:
                self.visual.down()
            elif command == self.commands.truncate:
                # limit the number of results
                num = utils.get_single_index(arg)
                if not num:
                    self.visual.error("Need number argument to apply result list truncation.")
                    continue
                self.max_search = num
                self.max_list = num
                # repeat last command, if applicable
                if previous_command is not None:
                    command = previous_command
            elif utils.is_index_list(command):
                # print(self.reference_entry_id_list)
                # for numeric input, select these entries
                self.select(user_input)
            elif command == self.commands.check:
                self.get_editor().check_consistency(self.entry_collection)
            else:
                self.visual.error("Undefined command: {}".format(command))
                self.visual.message("Available:")
                skeys = sorted(self.commands_dict.keys())
                self.visual.print_enum(list(zip(skeys, [self.commands_dict[k] for k in skeys])), at_most=None, header="action key".split())
            previous_command = command
        # end of loop
        self.save_if_modified()
