from collections import namedtuple
from thread.threaded import TimedThreadRunner

import clipboard

import utils
from command_parser import CommandParser
from config import Config
from decorators import *
from editor import Editor
from getters.getter import Getter
from reader.reader import Reader
from writer import Writer
from reader.entry import Entry
from search.searcher_factory import create_searcher
from selection import Selector
from visual.instantiator import setup


class Runner:
    search_invoke_counter = None
    is_running = True

    def __init__(self, conf, entry_collection=None):

        # configuration
        self.config = conf

        # assignments
        self.searcher = None
        self.getter = None
        self.editor = None
        self.sorter = None

        # read the bib database
        if entry_collection is None:
            rdr = Reader(conf)
            rdr.read()
            self.entry_collection = rdr.get_entry_collection()
        else:
            self.entry_collection = entry_collection

        # search settings
        self.searchable_fields = ["ID", "title"]
        self.multivalue_keys = ["author", "keywords"]
        self.searchable_fields += self.multivalue_keys

        # ui
        self.visual = setup(conf)

        # command and selection managers
        self.command_parser = CommandParser(self.config, self.visual)
        self.selector = Selector(self.visual)
        self.map_ids_to_functions()

        # history
        self.reset_history()
        self.search_invoke_counter = 0

    def get_max_search(self):
        if self.visual.handles_max_results:
            return None
        return self.config.get_search_result_size()

    def get_max_list(self):
        if self.visual.handles_max_results:
            return None
        return self.config.get_list_result_size()

    def test(self, kwargs):
        self.visual.log(f"Printing the func! {kwargs}")

    def get_current_entries(self):
        idxs = self.selector.get_selection(default_to_reference=True)
        ids = [self.reference_entry_id_list[i] for i in idxs]
        return [self.entry_collection.entries[eid] for eid in ids]

    def show_input_history(self):
        """Display the input history"""
        # copy with user multifilter
        pass

    def map_ids_to_functions(self):
        self.function_id_map = {}

        ctrls = {k: k for k in self.config.get_controls()}
        commands = utils.to_namedtuple(ctrls)
        self.function_id_map[commands.edit] = self.edit_entry
        self.function_id_map[commands.filter] = self.apply_filter
        self.function_id_map[commands.history_input] = self.show_input_history
        self.function_id_map[commands.bibtex_show] = self.show_raw_bibtex
        self.function_id_map[commands.bibtex_copy] = self.copy_raw_bibtex
        self.function_id_map[commands.history_back] = self.step_history
        self.function_id_map[commands.history_forward] = self.step_history
        self.function_id_map[commands.history_jump] = self.jump_history
        self.function_id_map[commands.history_reset] = self.reset_history
        self.function_id_map[commands.history_show] = self.show_history
        self.function_id_map[commands.history_log] = self.show_history_log
        self.function_id_map[commands.delete] = self.delete_entry
        self.function_id_map[commands.cite] = self.cite
        self.function_id_map[commands.cite_multi] = self.multi_cite
        self.function_id_map[commands.pdf_file] = self.set_local_pdf_path
        self.function_id_map[commands.pdf_web] = self.get_pdf_from_web
        self.function_id_map[commands.pdf_open] = self.pdf_open
        self.function_id_map[commands.pdf_search] = self.search_web_pdf
        self.function_id_map[commands.search] = self.search
        self.function_id_map[commands.list] = self.list
        self.function_id_map[commands.tag] = self.tag
        self.function_id_map[commands.get] = self.get_bibtex
        self.function_id_map[commands.save] = self.save_if_modified
        self.function_id_map[commands.clear] = self.clear
        self.function_id_map[commands.unselect] = self.selector.clear_cached
        self.function_id_map[commands.show] = self.show_entries
        self.function_id_map[commands.up] = self.visual.up
        self.function_id_map[commands.down] = self.visual.down
        self.function_id_map[commands.check] = self.check
        self.function_id_map[commands.settings] = self.edit_settings
        self.function_id_map[commands.merge] = self.merge
        self.function_id_map[commands.quit] = self.quit
        self.function_id_map[commands.debug] = self.debug
        self.function_id_map[commands.repeat] = self.command_parser.repeat_last
        self.function_id_map[self.command_parser.placeholder_index_list_id] = self.show_entries

        # do not archive some commands:
        # repeat, to avoid infiniloops
        # settings changes and screen clearing
        # selecting and unselecting
        self.command_parser.prevent_archiving(commands.repeat)
        self.command_parser.prevent_archiving(commands.settings)
        self.command_parser.prevent_archiving(commands.clear)
        self.command_parser.prevent_archiving(commands.unselect)

    def edit_settings(self, keyval=None):
        self.get_editor().edit_settings(keyval)
        # reset getter
        if self.getter is not None:
            self.getter = None

    @ignore_arg
    def clear(self):
        """Clearing function"""
        self.visual.clear()

    def show_raw_bibtex(self, entry_idx=None):
        """Display raw bibtex of the selection"""
        if entry_idx is None:
            entry_idx = self.selector.get_selection()
        else:
            entry_idx = self.selector.select_by_index(entry_idx)
        if not entry_idx:
            self.visual.error("Need a selection to show raw bibtex of")
            return
        self.visual.message(f"Displaying raw bibtex content of {len(entry_idx)} entries.")
        self.visual.newline()
        entries = self.get_current_entries()
        entries_string = Writer.entries_to_bibtex_string(entries)
        self.visual.print(entries_string)

    def copy_raw_bibtex(self, entry_idx=None):
        """Copy the raw bibtex of the selection"""
        if entry_idx is None:
            entry_idx = self.selector.get_selection()
        else:
            entry_idx = self.selector.select_by_index(entry_idx)
        if not entry_idx:
            self.visual.error("Need a selection to show raw bibtex of")
            return

        entries = self.get_current_entries()
        entries_string = Writer.entries_to_bibtex_string(entries)
        clipboard.copy(entries_string)
        self.visual.message(f"Copied raw bibtex content of {len(entries)} entries.")

    def edit_entry(self, entry_idx=None):
        if entry_idx is None:
            entry_idx = self.selector.get_selection()
        else:
            entry_idx = self.selector.select_by_index(entry_idx)
        if entry_idx is None:
            self.visual.error("Need a selection to edit")
            return
        for i in entry_idx:
            entry = self.entry_collection.entries[self.reference_entry_id_list[i]]
            updated_entry = Entry.from_string(self.get_editor().edit_entry_manually(entry))
            self.entry_collection.replace(updated_entry, old_id=entry.ID)
        # deselect
        self.selector.clear_cached()

    def apply_filter(self, filter_arg):
        """Apply a listing filter"""
        filtered_entries = self.visual.apply_filter(filter_arg, self.get_current_entries())
        # idxs = self.selector.select_by_objects(filtered_entries, yield_ones_index=True)
        self.visual.print_entries_enum(filtered_entries, None)
        # self.list(idxs)

    @ignore_arg
    def merge(self):
        """Add ocntents from the clipboard"""
        rdr = Reader(self.config)
        rdr.read_string(utils.paste(single_line=False))
        if len(rdr.get_entry_collection().entries) == 0:
            self.visual.error("Zero items extracted from the collection to merge.")
            return
        eids = []
        for entry in rdr.get_entry_collection().entries.values():
            self.entry_collection.add_new_entry(entry)
            eids.append(entry.ID)
        self.selector.update_reference(self.reference_entry_id_list)
        # select them
        res = self.selector.select_by_id(eids)
        if res is None:
            self.visual.error("Failed to select merged entry!")
        self.visual.log("Merged new entr{}:".format("y" if len(res) == 1 else "ies"))
        self.show_entries()

    @ignore_arg
    def quit(self):
        """Quitting flag-setting function"""
        self.visual.debug("Quitting!")
        self.is_running = False

    def search_for_entry(self, query):
        searcher = self.get_searcher()
        searcher.prepare(self.entry_collection.get_searchable_format(), self.config.get_config_file_dir(), self.get_max_search(), self.searchable_fields)
        breakpoint()
        results_ids = searcher.search(query)

        self.visual.print_entries_enum([self.entry_collection.entries[ID] for ID in results_ids], self.entry_collection, do_sort=False)
        return results_ids


    def get_bibtex(self, arg=None):
        """Function to fetch a bibtex"""
        getter = self.get_getter()
        if getter is None:
            return
        if not arg:
            arg = self.visual.ask_user(f"Search what on the web?", multichar=True)
            if not arg:
                self.visual.error("Nothing entered, aborting.")
                return
        try:
            res = getter.get_web_bibtex(arg)
        except Exception as ex:
            self.visual.error("Failed to complete the query: {}.".format(ex))
            return
        if not res:
            self.visual.error("No data retrieved.")
            return

        reader2 = Reader(self.config)
        read_entries_dict = reader2.read_entry_list(res)
        self.visual.log("Retrieved {} entry item(s) from query [{}]".format(len(read_entries_dict), arg))

        # select subset
        if len(read_entries_dict) > 1:
            ids, content = list(zip(*[(e.ID, e.get_discovery_view()) for e in read_entries_dict.values()]))
            _, selected_ids = self.visual.user_multifilter(content, header=Entry.discovery_keys, reference=ids)
            selected_entries = [v for (k, v) in read_entries_dict.items() if k in selected_ids]
        else:
            selected_entries = list(read_entries_dict.values())
        if not selected_entries:
            return
        self.visual.print_entries_contents(selected_entries)

        res = self.visual.ask_user("Store?", "*yes no-but-keep quit")
        if utils.matches(res, "yes"):
            selected_ids = []
            for entry in selected_entries:
                created_entry = self.entry_collection.add_new_entry(entry)
                if created_entry is None:
                    self.visual.error(f"Entry {entry.ID} already exists in the collection!")
                else:
                    selected_ids.append(created_entry.ID)
        elif utils.matches(res, "no-but-keep"):
            selected_ids = [x for x in selected_entries]
        elif utils.matches(res, "quit"):
            return
        if not selected_ids:
            return
        if self.visual.yes_no("Select it?"):
            self.selector.select_by_id(selected_ids)

        # pdf
        what = self.visual.ask_user("Pdf?", "local url web-search *skip")
        if utils.matches(what, "skip"):
            return
        if utils.matches(what, "url"):
            self.get_pdf_from_web()
            return
        if utils.matches(what, "local"):
            self.set_local_pdf_path()
            return
        if utils.matches(what, "web-search"):
            self.search_web_pdf()

    def pdf_open(self, arg=None):
        """Open the pdf of an entry"""
        nums = self.selector.select_by_index(arg)
        if not nums or nums is None:
            self.visual.print("Need a selection to open.")
        # arg has to be a single string
        if utils.has_none(nums):
            self.visual.print("Need a valid entry index.")
        for num in nums:
            entry_id = self.reference_entry_id_list[num]
            entry = self.entry_collection.entries[entry_id]
            pdf_in_entry = self.get_editor().open_pdf(entry)
            if not pdf_in_entry and len(nums) == 1:
                if self.visual.yes_no("Search for pdf on the web?"):
                    self.search_web_pdf()

    def tag(self, arg=None):
        """Add tag to an entry"""
        nums = self.selector.select_by_index(arg)
        if nums is None or not nums:
            self.visual.error("Need a selection to tag.")
            return
        for num in nums:
            entry = self.entry_collection.entries[self.reference_entry_id_list[num]]
            updated_entry = self.get_editor().tag(entry)
            if self.editor.collection_modified and updated_entry is not None:
                self.entry_collection.replace(updated_entry)
        self.editor.clear_cache()

    def search(self, query=None):
        """Entrypoint function for entries search
        """

        self.visual.log("Starting search")
        if self.search_invoke_counter > 0:
            # step to the starting history to search everything
            self.reset_history()
        search_done = False
        just_began_search = True
        query_supplied = bool(query)

        ttr = TimedThreadRunner(self.search_for_entry, "")
        # ttr.set_delay(1, self.visual.log, "delaying search execution...")

        while True:
            # get new search object, if it's a continued search OR no pre-given query
            if not just_began_search or (just_began_search and not query_supplied):
                search_done, new_query = self.visual.receive_search()
                self.visual.log("Got: [{}] [{}]".format(search_done, new_query))
                if search_done is None:
                    # pressed ESC
                    self.visual.message("Aborting search")
                    return
                if new_query == "" and search_done:
                    # pressed enter
                    self.visual.message("Concluded search")
                    break
                # got an actual query item
                # if query content is updated, reset the timer
                query = new_query

            query = query.lower().strip()
            # ttr.reset_time(query)
            # self.visual.log("Got query: {}".format(query))
            # ttr.update_args(query)
            # ttr.start()
            # ttr.stop()
            # results_ids = ttr.get_result()
            results_ids = self.search_for_entry(query)
            # results_ids = []
            just_began_search = False
            self.search_invoke_counter += 1
            if not self.visual.does_incremental_search:
                break

        if not query:
            # no search was performed
            return
        # push the reflist modification to history
        self.change_history(results_ids, "search:\"{}\"".format(query))

    # print entry, only fields of interest
    def show_entries(self, inp=None):
        """Print contents of the entries in the input"""
        nums = self.selector.select_by_index(inp)
        if not nums:
            # self.visual.error("No selection parsed to show.")
            return
        ids = [self.reference_entry_id_list[n] for n in nums]
        # self.visual.print("Entry #[{}]".format(ones_idx))
        self.visual.print_entries_contents([self.entry_collection.entries[ID] for ID in ids])

    def check(self, inp=None):
        # idxs = self.selector.select(inp)
        self.get_editor().check_consistency(self.entry_collection)

    # singleton getter fetcher
    def get_getter(self):
        if self.getter is None:
            self.getter = Getter(self.config)
        return self.getter

    # singleton searcher fetcher
    def get_searcher(self):
        if self.searcher is None:
            self.searcher = create_searcher(self.config.get_searcher())
        return self.searcher

    def get_editor(self):
        """singleton editor fetcher"""
        if self.editor is None:
            self.editor = Editor(self.config)
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
        self.selector.clear_cached()

    def debug(self):
        """Enter debug mode"""
        import ipdb; ipdb.set_trace()

    def list(self, arg=None):
        """List entries summary"""

        show_list = self.reference_entry_id_list
        nums = self.selector.select_by_index(arg, default_to_reference=True)
        if nums is None:
            # selection error
            return
        show_list = self.reference_entry_id_list
        if len(nums) > 0:
            # some indexes were selected
            show_list = [self.reference_entry_id_list[n] for n in nums]
            if show_list != self.reference_entry_id_list and arg is not None:
                # arguments specified directly; push the history change
                self.change_history(show_list, "{} {}".format("list", len(show_list)))
        else:
            # empty index list: show the entire reference
            pass
        self.visual.log("Listing {} entries.".format(len(show_list)))
        self.visual.print_entries_enum([self.entry_collection.entries[x] for x in show_list], self.entry_collection, at_most=self.get_max_list())

    def jump_history(self, index):
        """Jump to a specific history step"""
        if type(index) is str:
            index = utils.str_to_int(index)
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
        self.selector.update_reference(self.reference_entry_id_list)

    # move the reference list wrt stored history
    def step_history(self, n_steps=-1):
        """Function to step +/- n steps to history"""
        n_steps = utils.get_single_index(n_steps)
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
        self.selector.update_reference(self.reference_entry_id_list)

    def show_history(self):
        current_mark = ["" for _ in self.command_history]
        current_mark[self.reference_history_index] = "*"
        self.visual.print_enum(self.command_history, additionals=current_mark)
        self.visual.debug("History length: {}, history lengths: {}, current index: {}, current length: {}.".format(len(self.reference_history), [len(x) for x in self.reference_history], self.reference_history_index, len(self.reference_entry_id_list)))

    def show_history_log(self):
        """Display the history of past logs"""
        self.visual.print_enum(self.visual.history_log)

    def change_history(self, new_reflist, modification_msg):
        """Change the reference list to its latest modificdation

        Calling the function after a search will set the reference list to the resulting entry set.
        """
        self.visual.log("New reference list wrt: [{}], yielded {} items.".format(modification_msg, len(new_reflist)))
        self.push_reference_list(new_reflist, modification_msg)
        # unselect stuff -- it's meaningless now
        self.unselect()

    # add to reference list history
    def push_reference_list(self, new_list, command, force=False):
        # no duplicates or empty ref. list
        if (new_list == self.reference_entry_id_list or len(new_list) == 0) and not force:
            return
        # register the new reference
        self.reference_history.append(new_list)
        self.reference_history_index += 1
        self.reference_entry_id_list = new_list
        self.visual.message("Switching to new {}-long reference list.".format(len(self.reference_entry_id_list)))
        self.selector.update_reference(self.reference_entry_id_list)

        # store the command that produced it
        self.command_history.append((len(self.reference_entry_id_list), command))


    def save_if_modified(self, verify_write=True, called_explicitely=True):
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
        self.entry_collection.overwrite_file(self.config)
        self.entry_collection.reset_modified()


    def set_local_pdf_path(self, str_selection=None):
        """Function to attach a local pdf path to an entry"""
        nums = self.selector.select_by_index(str_selection)
        if nums is None or not nums or len(nums) > 1:
            self.visual.error("Need a single selection to set pdf to.")
            return
        entry = self.entry_collection.entries[self.reference_entry_id_list[nums[0]]]
        if entry.file is not None:
            if not self.visual.yes_no("Pdf attribute exists: {}, replace?".format(entry.file), default_yes=False):
                return
        updated_entry = self.get_editor().set_file(entry)
        if self.editor.collection_modified and updated_entry is not None:
            self.entry_collection.replace(updated_entry)
            self.visual.log("Entry {} updated with pdf path.".format(entry.ID))

    def delete_entry(self, arg):
        """Function to delete an entry"""
        nums = self.selector.select_by_index(arg)
        if nums is None or not nums:
            self.visual.error("Need a selection to delete.")
            return
        to_delete = [self.reference_entry_id_list[n] for n in nums]
        old_len, del_len = len(self.reference_entry_id_list), len(to_delete)
        for entry_id in to_delete:
            self.entry_collection.remove(entry_id)
            self.visual.log("Deleted entry {}".format(entry_id))
        remaining = [x for x in self.reference_entry_id_list if x not in to_delete]
        self.visual.log("Deleted {}/{} entries, left with {}".format(del_len, old_len, len(remaining)))
        self.push_reference_list(remaining, "deletion", force=True)
        self.unselect()

    def cite(self, arg=None):
        """Function to cite an entry"""
        nums = self.selector.select_by_index(arg)
        if nums is None or not nums:
            self.visual.error("Need a selection to cite.")
            return
        citation_id = ", ".join([self.reference_entry_id_list[n] for n in nums])
        citation = "\\cite{{{}}}".format(citation_id)
        # clipboard.copy(citation_id)
        clipboard.copy(citation)
        self.visual.message("Copied to clipboard: {}".format(citation))

    def multi_cite(self, arg=None):
        """Function to cite an entry for multi-entry citing"""
        nums = self.selector.select_by_index(arg)
        if nums is None or not nums:
            self.visual.error("Need a selection to multi-cite.")
            return
        citation_id = ", ".join([self.reference_entry_id_list[n] for n in nums])
        # clipboard.copy(citation_id)
        clipboard.copy(citation_id)
        self.visual.message("Copied to clipboard: {}".format(citation_id))


    def get_pdf_from_web(self, str_selection=None):
        nums = self.selector.select_by_index(str_selection)
        if nums is None or not nums or len(nums) > 1:
            self.visual.error("Need a single selection to download pdf to.")
            return
        entry_id = self.reference_entry_id_list[nums[0]]
        entry = self.entry_collection.entries[entry_id]
        if entry.file is not None:
            if not self.visual.yes_no("Pdf attribute exists: {}, replace?".format(entry.file), default_yes=False):
                return
        getter = Getter(self.config)
        pdf_url = self.visual.ask_user("Give pdf url to download", multichar=True)
        if pdf_url is None:
            return
        file_path = getter.download_web_pdf(pdf_url, entry_id)
        if file_path is None:
            self.visual.error("Failed to download from {}.".format(pdf_url))
            return
        updated_entry = self.get_editor().set_file(entry, file_path=file_path)
        self.entry_collection.replace(updated_entry)

    def search_web_pdf(self, str_selection=None):
        """Search the web for a pdf pertaining to the current entry selection
        """

        nums = self.selector.select_by_index(str_selection)
        if nums is None or not nums or len(nums) > 1:
            self.visual.error("Need a single selection to download pdf to.")
            return
        entry_id = self.reference_entry_id_list[nums[0]]
        entry = self.entry_collection.entries[entry_id]
        if entry.file is not None:
            if not self.visual.yes_no("Pdf attribute exists: {}, replace?".format(entry.file), default_yes=False):
                return
        pdf_path = self.get_getter().search_web_pdf(entry_id, self.get_searcher().preprocess_query(entry.title), entry.year)
        if pdf_path is None:
            self.visual.log("Invalid pdf path, aborting.")
            return
        updated_entry = self.get_editor().set_file(entry, file_path=pdf_path)
        if updated_entry is None:
            return
        self.entry_collection.replace(updated_entry)

    def loop(self, input_cmd=None):
        """Runner execution loop

        :param input_cmd: On-launch input from the user

        """
        while(self.is_running):
            command, arg = self.command_parser.get(input_cmd)
            self.visual.debug("Command: [{}] , arg: [{}]".format(command, arg))
            # call the appropriate function
            func = self.function_id_map[command]
            func(*arg)
            input_cmd = None

        # end of loop
        self.save_if_modified(called_explicitely=False)
        self.config.save_if_modified()
