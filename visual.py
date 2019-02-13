import json
import sys
import utils
from blessed import Terminal
from fuzzywuzzy import fuzz


# base class to get and print stuff
def setup(conf):
    visual_name = conf.visual
    if visual_name == Io.name:
        return Io.get_instance(conf)
    elif visual_name == Blessed.name:
        return Blessed.get_instance(conf)
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

    does_incremental_search = False

    def set_only_debug(self, val):
        self.only_debug = val

    def __init__(self, conf):
        self.do_debug = conf.debug

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
        opts = None
        opt_print = None
        default_option_idx = None
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

            opt_print = ["[{}]{}".format(x[0], x[1:]) for x in opts]
            if default_option_idx is not None:
                # add asterisk on print
                opt_print[default_option_idx] = self.default_option_mark + opt_print[default_option_idx]
            opt_print = " ".join(opt_print + explicit_opts)
            msg += " " + opt_print + ": "
        else:
            if msg:
                msg += ": "
        return msg, opts, opt_print, default_option_idx

    # func to show choices. Bang options are explicit and are not edited
    def ask_user(self, msg="", options_str=None, check=True, multichar=True):
        msg, opts, opt_print, default_option_idx = self.generate_user_responses(msg, options_str)
        while True:
            ans = self.get_raw_input(msg)
            if options_str:
                # default option on empty input
                if not ans and default_option_idx is not None:
                    return opts[default_option_idx]
                # loop on invalid input, if check
                if check:
                    if not utils.matches(ans, opts):
                        self.print("Valid options are: " + opt_print)
                        continue
            else:
                ans = ans.strip()
            # valid or no-option input
            return ans

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
        return "{:<{w}s}".format("\\cite{" + ID + "}", w=maxlen_id + 7)

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

    def print_enum(self, x_iter, at_most=None, additionals=None):
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
    def gen_entries_strings(self, entries, maxlens):
        enum_str_list = []
        for i, entry in enumerate(entries):
            enum_str_list.append(self.gen_entry_strings(entry, maxlens))
        return enum_str_list

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
        if len(x_iter) != len(entry_collection.entries):
            # recompute max lengths
            maxlen_id = max([len(x.ID) for x in x_iter])
            maxlen_title = max([len(x.title) for x in x_iter])
            maxlens = len(x_iter), maxlen_id, maxlen_title
        else:
            maxlens = entry_collection.maxlens()

        strings = ["{} {} {}".format(*tup) for tup in self.gen_entries_strings(x_iter, maxlens)]
        if additional_fields:
            strings = [s + f for (s, f) in zip(strings, additional_fields)]
        self.print_enum(strings, at_most=at_most)
        if print_newline:
            self.newline()

    def print_entry_contents(self, entry):
        if self.only_debug and not self.do_debug:
            return
        st = json.dumps(entry.get_pretty_dict(), indent=2)
        # remove enclosing {}
        st = " " + st.strip()[1:-1].strip()
        self.print(st)
        self.print("_" * 15)

    def print_entries_contents(self, entries):
        if self.only_debug and not self.do_debug:
            return
        for entry in entries:
            self.print_entry_contents(entry)

    def pause(self, msg):
        self.input(msg)



class Blessed(Io):
    name = "blessed"
    term = None
    instance = None
    search_cache = ""
    selection_cache = ""
    does_incremental_search = True
    message_buffer_size = None

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
        self.data_end_line = self.height -1
        self.data_buffer_size = self.data_end_line - self.data_start_line -3
        self.search_cache = ""
        self.prompt_in_use = False
        self.data_buffer = []

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

    def print(self, msg, temp=False, no_newline=False, use_buffer=False):
        if not msg:
            return
        if self.only_debug and not self.do_debug:
            return
        if use_buffer:
            self.clear_data()
            if not msg:
                return
            if self.only_debug and not self.do_debug:
                return
            # put lines to buffer
            msg = msg.split("\n")
            for i, line in enumerate(msg):
                if len(line) > self.width:
                    line = utils.limit_size(line, self.width)
                    msg[i] = line
            self.data_buffer.extend(msg)
            # restrict to size
            buffer_to_print = "\n".join(self.data_buffer[-self.data_buffer_size:])
            print(self.term.normal, buffer_to_print)
        else:
            print(self.term.normal, msg)


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
        # sys.stderr.write("{} {} ".format(x, y))
        c = self.get_raw_input()
        a = c
        breakpoint()
        self.message("Key:" + c)
        if c.is_sequence:
            # self.temp_print("got sequence: {0}, when inp is: [{1}].".format((str(c), c.name, c.code), inp), 30, 6)
            if c.name == "KEY_DELETE":
                self.clear_line(y, starting_x)
                self.search_cache = self.search_cache[:-1]
            elif c.name == "KEY_ENTER":
                self.search_cache = ""
                done = True
            elif c.name == "KEY_ESCAPE":
                self.search_cache = ""
                done = None
            else:
                self.message("Unhandled metakey:" + c.name)
                breakpoint()
        else:
            self.search_cache += c

        # candidate_commands = [cmd for cmd in self.commands if utils.matches(inp, cmd)]
        # for cmd in candidate_commands:
        #     if cmd == inp:
        #         self.clear_messages()
        #         return cmd
        # self.message(" ".join(candidate_commands))
        self.temp_print(self.search_cache, x, y)
        # self.temp_print(inp, x=30, y=self.y + 4)
        self.move(0, self.data_start_line)
        if done is False:
            self.clear_data()
        return done, self.search_cache

    def receive_command(self):
        x, y = self.layout.command
        starting_x = 2
        x += starting_x
        done = False
        info_msg = ""

        inp = self.selection_cache
        while not done:
            with self.term.cbreak():
                # get_character
                c = self.get_raw_input()
                if c.is_sequence:
                    if c.name == "KEY_DELETE":
                        self.clear_line(y, starting_x)
                        inp = inp[:-1]
                    elif c.name == "KEY_ENTER":
                        command = inp
                        self.selection_cache = ""
                        self.prompt_in_use = False
                        break
                    elif c.name == "KEY_ESCAPE":
                        # clear selection cache
                        self.selection_cache = ""
                        self.prompt_in_use = False
                        command = ""
                        break
                    else:
                        self.message("Got metakey: {}".format(c.name))
                        continue
                else:
                    inp += c

                # check for command match
                candidate_commands = self.get_candidate_commands(inp)
                exact_match = [inp == c for c in candidate_commands]
                if any(exact_match):
                    command = [candidate_commands[i] for i in range(len(exact_match)) if exact_match[i]][0]
                    command_name = [k for k in self.commands if self.commands[k] == command][0]
                    info_msg = "command: " + command_name
                    # display and break
                    self.temp_print(inp, x, y)
                    break

                # show possible command matches from current string
                if candidate_commands:
                    info_msg = " ".join(candidate_commands)
                else:
                    # no candidate commands -- check if it's a selection
                    if utils.is_index_list(inp) or self.selection_cache:
                        if not utils.is_valid_index_list(inp):
                            info_msg = "invalid selection"
                        else:
                            self.prompt_in_use = True
                            info_msg = "selection"
                            # if there's a cache, update it
                            self.selection_cache = inp
                            command = inp
                            # display and break
                            self.temp_print(inp, x, y)
                            break
                    else:
                        # invalid input: show suggestions starting from the last  valid sequence
                        # shave off that last invalid char
                        inp = inp[:-1]
                        if not inp:
                            info_msg = "Candidate commands: {}".format(" ".join(self.commands.values()))
                        else:
                            info_msg = "Candidate commands: {}".format(" ".join(self.get_candidate_commands(inp)))
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
        return [cmd for cmd in self.commands.values() if utils.matches(partial_str, cmd)]

    def clear_data(self):
        for line in (range(self.data_start_line, self.data_end_line)):
            self.clear_line(line)
        self.move(0, self.data_start_line)

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
        self.draw_lines()

        self.term.move(0, 0)
    def draw_lines(self):
        # top
        self.temp_print("_" * self.width, 0, self.layout.log[1] + 1)
        # bottom
        self.temp_print("_" * self.width, 0, self.layout.command[1] - 1)

    def temp_print(self, msg, x, y):
        # # skip the log line
        # yy = y + 1
        # clear the line to its end
        with self.term.location(x, y):
            # print("{} at {}, {}".format(msg, x, y))
            print("{}".format(msg))

    def newline(self):
        pass

    # printing funcs, add data clearing
    def print_entries_enum(self, x_iter, entry_collection, at_most=None, additional_fields=None, print_newline=False):
        self.clear_data()
        with self.term.location(0, self.data_start_line):
            Io.print_entries_enum(self, x_iter, entry_collection, at_most, additional_fields, print_newline)


    def print_entry_contents(self, entry, printing_multiple_entries=False):
        # self.clear_data()
        if not printing_multiple_entries:
            with self.term.location(0, self.data_start_line):
                Io.print_entry_contents(self, entry)
        else:
            Io.print_entry_contents(self, entry)
    # def search(self, query, candidates, at_most):
    #     return process.extract(query, candidates, limit=at_most)

    def print_entries_contents(self, entries):
        self.clear_data()
        with self.term.location(0, self.data_start_line):
            Io.print_entries_contents(self, entries)

    def print_enum(self, x_iter, at_most=None, additionals=None):
        self.clear_data()
        with self.term.location(0, self.data_start_line):
            Io.print_enum(self, x_iter, at_most, additionals)

    def error(self, msg):
        self.message("(!) {}".format(msg))

    def yes_no(self, msg, default_yes=True):
        opts = "*yes no" if default_yes else "yes *no"
        what = self.ask_user(msg, opts)
        if what is None:
            return what
        return utils.matches(what, "yes")

    # func to show choices. Bang options are explicit and are not edited
    def ask_user(self, msg="", options_str=None, check=True, multichar=False):
        msg, opts, opt_print, default_option_idx = self.generate_user_responses(msg, options_str)
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
                    if not utils.matches(ans, opts):
                        self.error("Valid options are: " + opt_print)
                        continue
            else:
                ans = ans.strip()
            # valid or no-option input
            return ans

    def input_multichar(self, x, y):
        """Input function that requres termination with RET or ESC
        """
        res = ""
        done = False
        while not done:
            key = self.get_raw_input()
            if key.is_sequence:
                # self.temp_print("got sequence: {0}, when inp is: [{1}].".format((str(c), c.name, c.code), inp), 30, 6)
                if key.name == "KEY_DELETE":
                    self.clear_line(y, x)
                    res = res[:-1]
                if key.name == "KEY_ENTER":
                    done = True
                if key.name == "KEY_ESCAPE":
                    res = None
                    done = True
            else:
                res += key
            self.temp_print(res, x, y)
        return res


if __name__ == '__main__':
    print("Do it.")
    t = Terminal()
    inp = ""
    while True:
        with t.cbreak():
            # c = self.term.inkey()
            # sys.stderr.write("{} {} ".format(x, y))
            with t.cbreak():
                c = t.inkey()
            if c.is_sequence:
                # self.temp_print("got sequence: {0}, when inp is: [{1}].".format((str(c), c.name, c.code), inp), 30, 6)
                if c.name == "KEY_DELETE":
                    with t.location(2, 10):
                        print(t.clear_eol())
                    inp = inp[:-1]
                if c.name == "KEY_ENTER":
                    break
            else:
                inp += c

            with t.location(2, 10):
                print(inp)
            # self.temp_print(inp, x=30, y=self.y + 4)



