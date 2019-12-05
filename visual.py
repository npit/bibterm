import json
from itertools import combinations

import terminaltables
from blessed import Terminal
from fuzzywuzzy import fuzz
from terminaltables import AsciiTable
from terminaltables.terminal_io import terminal_size

import utils


# base class to get and print stuff
def setup(conf):
    visual_name = conf.visual
    if visual_name == Io.name:
        return Io.get_instance(conf)
    elif visual_name == Blessed.name:
        return Blessed.get_instance(conf)
    elif visual_name == TermTables.name:
        return TermTables.get_instance(conf)
    else:
        print("Undefined ui config:", visual_name)
        exit(1)


class Io:
    name = "default"

    only_debug = False
    do_debug = False
    default_option_mark = "*"
    score_match_threshold = 50
    instance = None
    clear_size = 100
    prompt = ">"
    handles_max_results = None

    does_incremental_search = False

    def set_only_debug(self, val):
        self.only_debug = val

    def __init__(self, conf):
        self.do_debug = conf.debug
        self.handles_max_results = True

    def get_instance(conf=None):
        if Io.instance is not None:
            return Io.instance
        if conf is None:
            print("Need configuration to instantiate visual")
            exit(1)
        print("Instantiating the {} ui".format(Io.name))
        Io.instance = Io(conf)
        return Io.instance

    def clear(self):
        for _ in range(self.clear_size):
            self.newline()

    def idle(self):
        print("Give command: ", end="")

    def list(self, content):
        pass

    def print(self, msg=""):
        if self.only_debug and not self.do_debug:
            return
        print(msg)

    def fatal_error(self, msg):
        self.error(msg)
        exit(1)

    def log(self, msg):
        self.print(msg)

    def message(self, msg):
        self.print(msg)

    def error(self, msg):
        self.print("(!) {}".format(msg))

    def receive_command(self):
        return self.ask_user()

    def receive_search(self):
        return True, self.ask_user("Search:")

    def yes_no(self, msg, default_yes=True):
        opts = "*yes no" if default_yes else "yes *no"
        what = self.ask_user(msg, opts)
        if what is None:
            return what
        return utils.matches(what, "yes")

    def get_raw_input(self, msg):
        return input(msg)

    def generate_user_responses(self, msg, options_str):
        opts, opt_selection, opt_print, default_option_idx = [None] * 4
        if options_str is not None:
            opts = options_str.split()
            explicit_opts = [x[1:] for x in opts if x.startswith("#")]
            opts = [x for x in opts if not x.startswith("#")]

            default_option_idx = [i for i in range(len(opts)) if opts[i].startswith(self.default_option_mark)]
            if default_option_idx:
                if len(default_option_idx) > 1:
                    self.error("Multiple defaults:" + options_str)
                default_option_idx = default_option_idx[0]
                # remove asterisk from raw inputs
                opts[default_option_idx] = opts[default_option_idx][1:]

            # deduce the num. of letters required to distinguish opts
            num_letters_required = 1
            opt_combos = list(combinations(opts, 2))
            while True:
                if num_letters_required > max(list(map(len, opts))):
                    self.error("Indistinguishable options exist in options string: {}".format(options_str))
                if any([comb[0][:num_letters_required] == comb[1][:num_letters_required] for comb in opt_combos]):
                    num_letters_required += 1
                    continue
                break

            opt_selection = [c[:num_letters_required] for c in opts]
            opt_print = ["[{}]{}".format(x[:num_letters_required], x[num_letters_required:]) for x in opts]
            if default_option_idx:
                # add asterisk on print
                opt_print[default_option_idx] = self.default_option_mark + opt_print[default_option_idx]
            opt_print = " ".join(opt_print + explicit_opts)
            msg += " " + opt_print + ": "
        else:
            if msg:
                msg += ": "
        return msg, opts, opt_print, opt_selection, default_option_idx

    # func to show choices. Bang options are explicit and are not edited
    def ask_user(self, msg="", options_str=None, check=True, multichar=True, return_match=True):
        options_str = " ".join(options_str) if type(options_str) == list else options_str
        msg, opts, opt_print, opt_selection, default_option_idx = self.generate_user_responses(msg, options_str)
        while True:
            ans = self.get_raw_input(msg)
            if options_str:
                # default option on empty input
                if not ans and default_option_idx is not None:
                    return opts[default_option_idx]
                # loop on invalid input, if check
                if check:
                    # no exact match on full or required option lengths
                    if not any([ans == x for x in opt_selection + opts]):
                        self.print("Valid options are: " + opt_print)
                        continue

                # return matching entry from the options
                if return_match:
                    for x in opts:
                        if x.startswith(ans):
                            ans = x
                            break
            else:
                ans = ans.strip()
            # valid or no-option input
            return ans

    def user_multifilter(self, collection, header, reference=None):
        """Filtering function by user index selection. Reference can be used to keep track of input items"""
        if reference is None:
            reference = list(range(collection))

        cur_reference, cur_collection = reference, collection
        while True:
            self.print_enum(cur_collection, header=header)
            sel = self.ask_user("Enter numeric indexes to modify the list, or ENTER to proceed")
            sel = utils.get_index_list(sel, len(cur_collection))
            if sel:
                sel = sorted(set(sel))
                cur_collection = [cur_collection[i-1] for i in sel]
                cur_reference = [cur_reference[i-1] for i in sel]
                self.print_enum(cur_collection, header=header)
                if self.ask_user("Keep these?", "*yes no(reset)") == "yes":
                    return cur_collection, cur_reference
                else:
                    cur_collection = collection
                    cur_reference = reference
            else:
                return collection, reference

    def search(self, query, candidates, at_most, iterable_items=False):
        if iterable_items:
            # flatten
            nums = list(map(len, candidates))
            flattened_candidates = [c for clist in candidates for c in clist]
            # score
            raw_results = [(c, fuzz.partial_ratio(query, c)) for c in flattened_candidates]
            # argmax
            results, curr_idx = [], 0
            for n in nums:
                if n > 1:
                    max_val = max(raw_results[curr_idx: curr_idx + n], key=lambda x: x[1])
                else:
                    max_val = raw_results[curr_idx]
                results.append(max_val)
                # print("Got from: {} : {}".format(raw_results[curr_idx: curr_idx + n], max_val))
                curr_idx += n
        else:
            results = [(c, fuzz.partial_ratio(query, c)) for c in candidates]
        # assign index
        results = [(results[i], i) for i in range(len(results)) if results[i][1] >= self.score_match_threshold]
        results = sorted(results, key=lambda x: x[0][1], reverse=True)
        return results[:at_most]
        # return process.extract(query, candidates, limit=at_most)

    def newline(self):
        self.print()

    def title_str(self, title, maxlen_title):
        return "{:<{w}s}".format(title, w=maxlen_title)

    def ID_str(self, ID, maxlen_id):
        # return "{:<{w}s}".format("\\cite{" + ID + "}", w=maxlen_id + 7)
        if maxlen_id is not None:
            return "{:<{w}s}".format(ID, w=maxlen_id + 7)
        return ID

    def keyword_str(self, keywords):
        if keywords is None or not keywords:
            return ""
        return "({})".format(", ".join(keywords))

    def num_str(self, num, maxnum):
        numpad = len(str(maxnum)) - len(str(num))
        return "[{}]{}".format(num, " " * numpad)

    # enumerate a collection with indexes
    def enum(self, x_iter):
        return ["{} {}".format(self.num_str(i + 1, len(x_iter)), x_iter[i]) for i in range(len(x_iter))]

    def print_enum(self, x_iter, at_most=None, additionals=None, header=None):
        if self.only_debug and not self.do_debug:
            return
        # check which items will be printed
        if at_most and len(x_iter) > at_most:
            idxs_print = list(range(at_most - 1)) + [len(x_iter) - 1]
        else:
            idxs_print = list(range(len(x_iter)))

        printed_dots = False
        for i, s in enumerate(self.enum(x_iter)):
            if i in idxs_print:
                if additionals:
                    self.print(s + additionals[i])
                else:
                    self.print(s)
            else:
                if not printed_dots:
                    self.print("...")
                    printed_dots = True

    def gen_entry_strings(self, entry, maxlens):
        return (self.ID_str(entry.ID, maxlens[1]), self.title_str(entry.title, maxlens[2]), self.keyword_str(entry.keywords))

    def gen_entry_enum_strings(self, entry, maxlens, num, max_num=None):
        if max_num is None:
            max_num = maxlens[0]
        return (self.num_str(num, max_num), self.ID_str(entry.ID, maxlens[1]),
                self.title_str(entry.title, maxlens[2]), self.keyword_str(entry.keywords))

    # produce enumeration strings
    def gen_entries_strings(self, entries, additional_fields):
        maxlen_id = max([len(x.ID) for x in entries])
        maxlen_title = max([len(x.title) for x in entries])
        maxlens = len(entries), maxlen_id, maxlen_title
        enum_str_list = []
        for i, entry in enumerate(entries):
            st = self.gen_entry_strings(entry, maxlens)
            if additional_fields:
                st += additional_fields[i]
            enum_str_list.append(self.gen_entry_strings(entry, maxlens))
        return enum_str_list

    # print iff in debug mode
    def debug(self, msg):
        if not self.do_debug:
            return
        self.print("debug: {}".format(msg))

    # print a list of entries
    def print_entries_enum(self, x_iter, entry_collection, at_most=None, additional_fields=None, print_newline=False):
        if self.only_debug and not self.do_debug:
            return
        if not x_iter:
            return
        strings = ["{} {} {}".format(*tup) for tup in self.gen_entries_strings(x_iter, additional_fields)]
        self.print_enum(strings, at_most=at_most)
        if print_newline:
            self.newline()

    def get_entry_contents(self, entry):
        if type(entry) != dict:
            entry = entry.get_pretty_dict()
        return entry

    def get_entry_details(self, entry):
        return entry.get_raw_dict()
        # st = json.dumps(entry, indent=2)
        # # remove enclosing {}
        # st = " " + st.strip()[1:-1].strip()
        # return st + " \n{}".format("_" * 15)

    def print_entry_contents(self, entry):
        if self.only_debug and not self.do_debug:
            return
        st = json.dumps(self.get_entry_contents(entry), indent=2)
        # remove enclosing {}
        st = " " + st.strip()[1:-1].strip()
        st += st + " \n{}".format("_" * 15)
        self.print(st)

    def print_entries_contents(self, entries):
        if self.only_debug and not self.do_debug:
            return
        for entry in entries:
            self.print_entry_contents(entry)

    def pause(self, msg=""):
        self.ask_user(msg)

    def up(self):
        pass

    def down(self):
        pass



class TermTables(Io):
    name = "ttables"

    def __init__(self, conf):
        Io.__init__(self, conf)

    @staticmethod
    def get_instance(conf=None):
        if TermTables.instance is not None:
            return TermTables.instance
        if conf is None:
            self.error("Need configuration to instantiate visual")
        print("Instantiating the {} ui".format(TermTables.name))
        TermTables.instance = TermTables(conf)
        return TermTables.instance

    def gen_entry_strings(self, entry, maxlens=None):
        # do not limit / pad lengths
        return (self.ID_str(entry.ID, None), self.title_str(entry.title, len(entry.title)), self.keyword_str(entry.keywords))

    def print_entries_enum(self, x_iter, entry_collection, at_most=None, additional_fields=None, print_newline=False):
        if self.only_debug and not self.do_debug:
            return
        if not x_iter:
            return
        entries_strings = self.gen_entries_strings(x_iter, additional_fields)
        # strings = ["{} {} {}".format(*tup) for tup in entries_strings]
        self.print_enum(entries_strings, at_most=at_most, header=["id", "title", "tags"], preserve_col_idx=[0])
        if print_newline:
            self.newline()

    def print_entries_contents(self, entries, header=None):
        """Function to print all available entry information in multiple rows"""
        if self.only_debug and not self.do_debug:
            return
        if header is None:
            header = ["attribute", "value"]
        contents = [list(self.get_entry_details(cont).items()) for cont in entries]
        self.print_multiline_items(contents, header)

    def print_multiline_items(self, items, header):
        """Print single-column (plus enumeration) multiline items"""
        header = ["idx"] + header
        table_contents = [header]
        if len(header) != len(table_contents[0]):
            self.error("Header length mismatch!")
            return
        num = 0
        for item in items:
            num += 1
            attributes, values = [], []
            for (name, value) in item:
                attributes.append(str(name))
                values.append(str(value))
            table_contents.append([str(num), "\n".join(attributes).strip(), "\n".join(values).strip()])
        self.print(self.get_table(table_contents, preserve_col_idx=[0], inner_border=True, is_multiline=True))

    def get_table(self, contents, preserve_col_idx=[], inner_border=False, is_multiline=True):
        table = self.fit_table(AsciiTable(contents), preserve_col_idx, is_multiline)
        if inner_border:
            table.inner_row_border = True
        return table.table

    def print_entry_contents(self, entry):
        if self.only_debug and not self.do_debug:
            return
        contents = self.get_entry_contents(entry)
        contents = [["attribute", "value"]] + list(contents.items())
        self.print(self.get_table(contents).table)


    def fit_table(self, table, preserve_col_idx=None, is_multiline=False):
        change_col_idx = range(len(table.table_data[0]))
        if preserve_col_idx is not None:
            change_col_idx = [i for i in change_col_idx if i not in preserve_col_idx]
            change_col_idx = sorted(change_col_idx, reverse=True)

        while not table.ok:
            data = table.table_data
            if not change_col_idx:
                self.fatal_error("Table does not fit but no changeable columns defined.")
            widths = [[len(x) for x in row] for row in data]
            zwidths = list(zip(*widths))
            # med = zwidths[len(zwidths)//2]
            # mean_lengths = [sum(x)/len(x) for x in zwidths]
            # anything larger than 2 * the median, prune it
            termwidth = terminal_size()[0]
            maxwidths = [max(z) for z in zwidths]
            max_column_sizes = [table.column_max_width(k) for k in range(len(data[0]))]
            # calc the required reduction; mx is negative for overflows
            # max_size_per_col = [mw - mcs if mcs < 0 else mw for (mw, mcs) in zip(maxwidths, max_column_sizes)]
            # get widths for each row
            for col in change_col_idx:
                max_sz = max_column_sizes[col]
                if max_sz < 0:
                    # column's ok
                    continue
                for row, row_widths in enumerate(widths):
                    col_width = row_widths[col]
                    if col_width > max_sz:
                        # prune the corresponding column
                        data[row][col] = self.prune_string(data[row][col], max_sz)
                        widths[row][col] = len(data[row][col])
            table = AsciiTable(data)
        return table

    def prune_string(self, content, prune_to=None, repl="..."):
        # consider newlines
        if "\n" in content:
            content = content.split("\n")
            pruned = [self.prune_string(ccc, prune_to, repl) for ccc in content]
            return "\n".join(pruned)
        if len(content) > prune_to:
            to = max(0, prune_to - len(repl))
            content = content[:to] + repl
        return content

    def print_enum(self, x_iter, at_most=None, additionals=None, header=None, preserve_col_idx=None):
        """Print collection, with a numeric column per line"""
        if preserve_col_idx is None:
            preserve_col_idx = []
        if self.only_debug and not self.do_debug:
            return
        x_iter = utils.listify(x_iter)
        # check which items will be printed
        if at_most is not None and len(x_iter) > at_most:
            idxs_print = list(range(at_most - 1)) + [len(x_iter) - 1]
            dots = ["..."] * (len(x_iter[0]) + 1) # +1 for the enumeration
        else:
            idxs_print = list(range(len(x_iter)))
            dots = None

        table_data = []
        for i, row in enumerate(x_iter):
            if i in idxs_print:
                try:
                    len(row)
                except:
                    row = [row]
                row = [str(r) for r in row]
                table_data.append([str(i+1)] + row)
        if dots:
            table_data.insert(len(table_data)-1, dots)

        if header:
            table_data = [["idx"] +  header] + table_data
        preserve_col_idx = [0] + [p+1 for p in preserve_col_idx]
        table = self.get_table(table_data, preserve_col_idx=preserve_col_idx)

        self.newline()
        self.print(table)

class Blessed(Io):
    name = "blessed"
    term = None

    instance = None
    search_cache = ""
    search_cache_underflow = None
    selection_cache = ""
    does_incremental_search = True
    message_buffer_size = None
    use_buffer = None

    # metakey handling (e.g. C-V)
    key_codes = {'\x16': ('C-V', lambda x: utils.paste())
                 }

    def get_metakey(self, key):
        if key in self.key_codes:
            return self.key_codes[key]
        return None

    class states:
        command = "command"
        search = "command"
    curren_state = None

    class positions:
        lower_left = None
        upper_left = None

    class layout:
        command = None
        log = None
        message = None
        large_message = None
        prompt_in_use = None

    def initialize_layout(self):
        # initialize positions
        self.positions.lower_left = 0, self.height
        self.positions.upper_left = 0, 0
        self.positions.lower_right = self.width, self.height
        self.positions.upper_right = self.width, 0

        try:
            layout = json.load(self.conf.layout)
            self.layout = utils.to_namedtuple(layout, 'layout')
        except:
            self.layout.command = self.positions.lower_left
            self.layout.log = self.positions.upper_left
            self.layout.message = (self.width // 3, self.height)
            self.layout.debug = (self.width // 3, self.height - 2)
            self.layout.large_message = (2 * self.width // 3, 1)

            self.command_buffer_size = self.layout.message[0] - 1
            self.message_buffer_size = self.width - self.layout.message[0]
            self.log_buffer_size = self.width

        self.curren_state = self.states.command

    def __init__(self, conf):
        self.conf = conf
        self.term = Terminal()
        self.width = self.term.width
        self.height = self.term.height - 2
        self.initialize_layout()
        self.clear()
        self.data_start_line = 2
        self.data_end_line = self.height - 1
        self.data_buffer_size = self.data_end_line - self.data_start_line - 3
        self.search_cache = ""
        self.search_cache_underflow = False
        self.prompt_in_use = False
        self.data_buffer = []
        self.handles_max_results = False
        self.viewport_top = 0
        self.use_buffer = False

        # controls
        self.commands = conf.controls
        self.selection_commands = conf.selection_commands

    def log(self, msg):
        self.clear_line(self.layout.log[1])
        with self.term.location(*self.layout.log):
            print(utils.limit_size(msg, self.log_buffer_size))

    def get_instance(conf=None):
        if Blessed.instance is not None:
            return Blessed.instance
        if conf is None:
            utils.error("Need configuration to instantiate visual")
        print("Instantiating the {} ui".format(Blessed.name))
        Blessed.instance = Blessed(conf)
        return Blessed.instance

    def set_viewport(self, top_line):
        self.viewport_top = top_line
        self.print()

    def print(self, msg=None, temp=False, no_newline=False, limit_dots=False):
        if self.only_debug and not self.do_debug:
            return
        # truncate overly long lines
        # put lines to current dimensions
        if msg:
            if type(msg) != list:
                msg = msg.strip().split("\n")
            msg = [utils.limit_size(x.strip(), self.width - 1) for x in msg]

        if self.use_buffer:
            self.clear_data()
            if msg:
                self.data_buffer.extend(msg)
            # restrict to size
            if limit_dots:
                # show the last line, and fill line before it with dots
                buffer_to_print = self.data_buffer[self.viewport_top: self.data_buffer_size - 2]
                buffer_to_print.append("...")
                buffer_to_print.append(self.data_buffer[-1])
            else:
                # show the section that fits wrt the viewport
                buffer_to_print = self.data_buffer[self.viewport_top:self.viewport_top + self.data_buffer_size]
                self.log("Using viewport bounds: {} {}".format(self.viewport_top, self.viewport_top + self.data_buffer_size))
            buffer_to_print = self.enum(buffer_to_print)
            buffer_to_print = "\n".join(buffer_to_print)
            self.temp_print(buffer_to_print, 0, self.data_start_line)
        else:
            msg = msg[0:self.data_buffer_size]
            msg = "\n".join(msg)
            # self.pause()
            self.temp_print(msg, 0, self.data_start_line)
            # self.pause()

    def clear(self):
        print(self.term.clear())

    def get_raw_input(self, msg=None, coords=None):
        with self.term.cbreak():
            c = self.term.inkey()
        if coords is not None:
            if not c.is_sequence:
                self.temp_print(c, *coords)
        return c

    def get_position_by_state(self):
        if self.curren_state == self.states.command:
            return self.layout.command

    def receive_search(self):
        done = False
        if not self.search_cache:
            self.clear_prompt()
            self.update_prompt_symbol("/")
        x, y = self.layout.command
        starting_x = 2
        x += starting_x

        # get_character
        key = self.input_multichar(x, y, single_char=True, initial_entry=self.search_cache)
        if key == self.search_cache:
            if not self.search_cache_underflow:
                # enter key or consecutive deletes
                done = True
            self.search_cache = ""
        elif key is None:
            # escape key
            done = None
            self.search_cache = ""
        else:
            self.search_cache = key
            self.search_cache_underflow = False
        if done is False:
            self.clear_data()
        self.message("{} {}".format(done, self.search_cache))
        # self.pause()
        return done, self.search_cache

    def get_command_full_name(self, cmd):
        return [k for k in self.commands if self.commands[k] == cmd][0]

    def match_command(self, inp):
        candidate_commands = self.get_candidate_commands(inp)
        exact_match = [inp == c for c in candidate_commands]
        if any(exact_match):
            exact_command = [candidate_commands[i] for i in range(len(exact_match)) if exact_match[i]][0]
        else:
            exact_command = None
        return candidate_commands, exact_command

    def conditional_clear_selection(self, command):
        """Clear the selection cache on selecton-unrelated commands
        """
        if not self.selection_cache:
            return
        if command not in self.selection_commands:
            self.selection_cache = ""
            self.debug_message("Cleared selection")

    def receive_command(self):
        x, y = self.layout.command
        starting_x = 2
        x += starting_x
        done = False
        info_msg = ""

        inp = self.selection_cache
        while not done:
            command = ""
            # input
            new_inp = self.input_multichar(starting_x, y, single_char=True, initial_entry=inp)
            # esc
            if new_inp is None:
                self.selection_cache = ""
                self.prompt_in_use = False
                command = None
                break
            # enter
            if new_inp == inp:
                self.selection_cache = ""
                self.prompt_in_use = False
                command = inp
                break
            # del to empty
            if not new_inp:
                self.selection_cache = ""
                self.prompt_in_use = False
                break
            inp = new_inp

            self.debug_message("Sel. cache: [{}]".format(self.selection_cache))

            # check for command match
            candidate_commands, exact_command = self.match_command(inp)
            if exact_command:
                info_msg = "command: " + self.get_command_full_name(exact_command)
                self.temp_print(inp, x, y)
                command = exact_command
                # if the matched is not selection-related, clear the selection
                self.conditional_clear_selection(command)
                break

            # show possible command matches from current string
            if candidate_commands:
                info_msg = "<{}>".format(" ".join(candidate_commands))
            else:
                # no candidate commands
                # if current string is a valid selection, update it
                if utils.is_index_list(inp):
                    self.prompt_in_use = True
                    # set selection cache
                    self.selection_cache = inp
                    info_msg = "selection: {}".format(self.selection_cache)
                    command = inp
                    # display and break
                    self.temp_print(inp, x, y)
                    break
                elif self.selection_cache:
                    # not valid selection, but previous one was
                    new_inp = inp[len(self.selection_cache):]
                    # if extraneous input is a command, partial or not, show it
                    candidate_commands, exact_command = self.match_command(new_inp)
                    if exact_command:
                        self.debug_message('Selection cmd')
                        # apply exact command on selection
                        info_msg = "command: " + self.get_command_full_name(exact_command)
                        self.temp_print(inp, x, y)
                        command = exact_command + " " + self.selection_cache
                        done = True
                    elif candidate_commands:
                        # show partial
                        info_msg = "<{}> {}".format(" ".join(candidate_commands), self.selection_cache)
                        self.debug_message('Selection partial')
                    else:
                        info_msg = "Invalid selection / selection-command: {}".format(inp)
                        self.debug_message('Invalid selection cmd')
                else:
                    # wholly invalid input: shave off that last invalid char
                    inp = inp[:-1]
                    #  show suggestions starting from the last  valid sequence
                    info_msg = "Candidate commands: {}".format(" ".join(self.commands.values()))
                    self.message(info_msg)

            # show current entry
            self.temp_print(inp, x, y)
            self.message(info_msg)

        self.clear_prompt()
        if self.selection_cache:
            self.temp_print(self.selection_cache, x, y)
        self.message(info_msg)
        return command

    def get_candidate_commands(self, partial_str):
        if not partial_str:
            return self.commands.values()
        return [cmd for cmd in self.commands.values() if utils.matches(partial_str, cmd)]

    def clear_data(self):
        for line in (range(self.data_start_line, self.data_end_line)):
            self.clear_line(line)
        # self.move(0, self.data_start_line)

    def clear_messages(self):
        self.clear_line(self.layout.message[1], self.layout.message[0])

    def message(self, msg, large=False):
        self.clear_messages()
        msg = utils.limit_size(msg, self.message_buffer_size)
        # self.temp_print(msg, *self.layout.large_message)
        self.temp_print(msg, *self.layout.message)

    def update_prompt_symbol(self, prompt):
        self.temp_print(prompt, *self.layout.command)
        coords = self.layout.command[0] + len(prompt) + 1, self.layout.command[1]
        return coords

    def clear_prompt(self):
        # self.clear_line(self.layout.command[1], self.layout.message[0])
        self.temp_print(" " * self.command_buffer_size, *self.layout.command)

    def clear_line(self, line_num, start_x=0):
        with self.term.location(start_x, line_num):
            print(self.term.clear_eol())

    def move(self, x, y):
        print(self.term.move(x, y))

    def idle(self):
        # prompt
        if not self.prompt_in_use:
            self.clear_prompt()
            self.update_prompt_symbol(self.prompt)

        # divider lines
        # self.draw_lines()

        # self.term.move(0, self.data_start_line)

    def draw_lines(self):
        self.message("Top {} bottom {}".format(self.layout.log[1] + 1, self.layout.command[1] - 1))
        # top
        self.pause("paused...")
        self.temp_print("<" + ("_" * (self.width - 2)) + ">", 0, self.layout.log[1] + 1)
        # bottom
        self.temp_print("<" + ("_" * (self.width - 2)) + ">", 0, self.layout.command[1] - 1)

    def temp_print(self, msg, x, y):
        # # skip the log line
        # yy = y + 1
        # clear the line to its end
        with self.term.location(x, y):
            # print("{} at {}, {}".format(msg, x, y))
            print("{}".format(msg))

    def debug_message(self, msg):
        # if self.only_debug and not self.do_debug:
        #     return
        self.temp_print("debug: " + msg, *self.layout.debug)

    def newline(self):
        pass

    # printing funcs, add data clearing
    def print_entries_enum(self, x_iter, entry_collection, at_most=None, additional_fields=None, print_newline=False):
        self.clear_data()
        with self.term.location(0, self.data_start_line):
            Io.print_entries_enum(self, x_iter, entry_collection, at_most, additional_fields, print_newline)

    def print_entries_contents(self, entries):
        self.clear_data()
        with self.term.location(0, self.data_start_line):
            entry_contents_str = "\n".join([self.get_entry_contents(entry) for entry in entries])
            self.print(entry_contents_str)

    def print_enum(self, x_iter, at_most=None, additionals=None):
        self.clear_data()
        with self.term.location(0, self.data_start_line):
            # Io.print_enum(self, x_iter, at_most, additionals)
            self.print(self.enum(x_iter))

    def error(self, msg):
        self.message("(!) {}".format(msg))

    def yes_no(self, msg, default_yes=True):
        opts = "*yes no" if default_yes else "yes *no"
        what = self.ask_user(msg, opts)
        if what is None:
            return what
        return utils.matches(what, "yes")

    # func to show choices. Bang options are explicit and are not edited
    def ask_user(self, msg="", options_str=None, check=True, multichar=False, return_match=False):
        msg, opts, opt_print, opt_selection, default_option_idx = self.generate_user_responses(msg, options_str)
        self.clear_prompt()
        prompt_input_coords = self.update_prompt_symbol(msg)
        while True:
            if multichar:
                ans = self.input_multichar(*prompt_input_coords)
            else:
                ans = self.get_raw_input(coords=prompt_input_coords)
            if ans is None:
                return None
            ans = str(ans).strip()

            if options_str:
                # default option on empty input
                if not ans and default_option_idx is not None:
                    return opts[default_option_idx]
                # loop on invalid input, if check
                if check:
                    if not any([ans == x for x in opt_selection + opts]):
                        self.error("Valid options are: " + opt_print)
                        continue
                # return matching entry from the options
                if return_match:
                    for x in opts:
                        if x.startswith(ans):
                            ans = x
            else:
                ans = ans.strip()
            # valid or no-option input
            return ans

    def input_multichar(self, x, y, single_char=False, initial_entry=None):
        """Input function that requres termination with RET or ESC
        """
        if initial_entry is not None:
            res = initial_entry
        else:
            res = ""
        done = False
        while not done:
            key = self.get_raw_input()
            if self.get_metakey(key):
                # metakey handling
                name, func = self.get_metakey(key)
                self.debug_message("Metakey: {}".format(name))
                res += func(key)
            elif key.is_sequence:
                # blessed sequence key
                if key.name == "KEY_DELETE":
                    self.clear_line(y, x)
                    if not res:
                        # manage potential search_cache underflow
                        self.search_cache_underflow = True
                    res = res[:-1]
                if key.name == "KEY_ENTER":
                    # on enter, we're done
                    done = True
                if key.name == "KEY_ESCAPE":
                    # on escape, return nothing
                    res = None
                    done = True
            else:
                # regular input
                res += key
            # print current entry
            self.temp_print(res, x, y)
            # for single-char mode, return immediately
            if single_char:
                break
        return res

    def up(self):
        if not self.use_buffer:
            return
        self.set_viewport(max(self.viewport_top - 1, 0))

    def down(self):
        if not self.use_buffer:
            return
        highest_viewport_top = len(self.data_buffer) - self.data_buffer_size
        self.set_viewport(min(highest_viewport_top, self.viewport_top + 1))
        self.message("highest vp {}" + str(highest_viewport_top))
