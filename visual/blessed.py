import threading

import utils
from blessed import Terminal
# from visual.io import Io
from visual.termtables import TermTables


class pos:
    def __init__(self, x=-1, y=-1):
        self.x = x
        self.y = y
        self.w = 0
        self.h = 0
    def values(self):
        return self.x, self.y
    def above(self):
        return pos(self.x, self.y -1)
    def below(self):
        return pos(self.x, self.y +1)
    def clone(self):
        return pos(self.x, self.y)
    def __str__(self):
        return str((self.x, self.y, self.w, self.h))


class Blessed(TermTables):
    name = "blessed"
    term = None

    instance = None
    search_cache = ""
    search_cache_underflow = None
    selection_cache = ""
    does_incremental_search = True
    message_buffer_size = None
    use_buffer = None

    access_lock = None

    search_time_delta = 1

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


    class landmarks:
        lower_left = pos()
        upper_left = pos()

    class layout:
        command = pos()
        log = pos()
        message = pos()
        large_message = pos()
        data = pos()

    def initialize_layout(self):
        # initialize landmarks
        self.landmarks.lower_left = pos(0, self.height)
        self.landmarks.upper_left = pos(0, 0)
        self.landmarks.lower_right = pos(self.width, self.height)
        self.landmarks.upper_right = pos(self.width, 0)

        try:
            layout = json.load(self.conf.layout)
            self.layout = utils.to_namedtuple(layout, 'layout')
        except:
            self.use_separator_lines = True
            self.layout.log = self.landmarks.upper_left
            self.layout.log.w = self.width

            self.layout.command = self.landmarks.lower_left
            self.layout.command.w = self.width // 4
            self.layout.debug = self.layout.command.above()
            self.layout.debug.w = self.width
            self.layout.message = pos(self.width // 3, self.height)
            self.layout.message.w = self.width //3
            self.layout.large_message = pos(2 * self.width // 3, 1)

            self.command_buffer_size = self.layout.message.x - 1
            self.message_buffer_size = self.width - self.layout.message.x
            self.log_buffer_size = self.width
            self.debug_buffer_size = self.width

            self.layout.data = self.layout.log.below()
            if self.use_separator_lines:
                self.layout.data = self.layout.data.below()

            self.layout.data.w = self.width
            self.layout.data.h = self.layout.debug.y - 1 - self.layout.data.y
            if self.use_separator_lines:
                self.layout.data.h -=1


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

        # threading lock
        self.access_lock = threading.Lock()

    def print_to_layout(self, msg, prompt, layout, do_clear=True, max_size=None):
        if do_clear:
            self.clear_line(layout.y, layout.x)
        self.temp_print(prompt + ": " + msg, *layout.values(), max_size=max_size)

    def log(self, msg):
        self.access_lock.acquire()
        self.log_history.append(msg)
        self.print_to_layout(msg, "Log", self.layout.log, do_clear=True, max_size=self.layout.log.w)
        self.access_lock.release()

    def command(self, msg):
        if msg is None:
            msg = ""
        self.print_to_layout(msg, "Command", self.layout.command, do_clear=True, max_size=self.layout.command.w)

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
        # self.print()

    def print(self, msg=None, temp=False, no_newline=False, limit_dots=False):
        if self.only_debug and not self.do_debug:
            return
        # truncate overly long lines
        # put lines to current dimensions
        if msg:
            if type(msg) != list:
                msg = msg.strip().split("\n")
            msg = [utils.limit_size(x.strip(), self.width) for x in msg]

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
            msg = msg[0:self.layout.data.h]
            msg = "\n".join(msg)
            self.temp_print(msg, 0, self.layout.data.y)

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
            return self.layout.command.values()

    def receive_search(self):
        done = False
        if not self.search_cache:
            self.clear_prompt()
            self.update_prompt_symbol("/")
        x, y = self.layout.command.values()
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
        self.message("rcv. search: {} {}".format(done, self.search_cache))
        # update potentially fudged borders
        self.draw_static()
        # return results
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
            self.debug("Cleared selection")

    def receive_command(self):
        x, y = self.layout.command.values()
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

            self.debug("Sel. cache: [{}]".format(self.selection_cache))

            # check for command match
            candidate_commands, exact_command = self.match_command(inp)
            if exact_command:
                info_msg = "command: " + self.get_command_full_name(exact_command)
                command = exact_command
                # if the matched is not selection-related, clear the selection
                # self.conditional_clear_selection(command)
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
                    break
                elif self.selection_cache:
                    # not valid selection, but previous one was
                    new_inp = inp[len(self.selection_cache):]
                    # if extraneous input is a command, partial or not, show it
                    candidate_commands, exact_command = self.match_command(new_inp)
                    if exact_command:
                        self.debug('Selection cmd')
                        # apply exact command on selection
                        info_msg = "command: " + self.get_command_full_name(exact_command)
                        command = exact_command + " " + self.selection_cache
                        done = True
                    elif candidate_commands:
                        # show partial
                        info_msg = "<{}> {}".format(" ".join(candidate_commands), self.selection_cache)
                        self.debug('Selection partial')
                    else:
                        info_msg = "Invalid selection / selection-command: {}".format(inp)
                        self.debug('Invalid selection cmd')
                else:
                    # wholly invalid input: shave off that last invalid char
                    inp = inp[:-1]
                    #  show suggestions starting from the last  valid sequence
                    info_msg = "Candidate commands: {}".format(" ".join(self.commands.values()))
                    self.message(info_msg)

            # show current command entry
            self.command(inp)
            # self.temp_print(inp, x, y)
            self.message(info_msg)

        # self.clear_prompt()
        # if self.selection_cache:
        #     self.temp_print(self.selection_cache, x, y)
        # self.message(info_msg)
        self.clear_data()
        self.command(command)
        return command

    def get_candidate_commands(self, partial_str):
        if not partial_str:
            return self.commands.values()
        return [cmd for cmd in self.commands.values() if utils.matches(partial_str, cmd)]

    def clear_data(self):
        for line in range(self.layout.data.y, self.layout.data.y + self.layout.data.h):
            self.clear_line(line)
        # self.move(0, self.data_start_line)

    def clear_prompt(self):
        self.temp_print(" " * self.command_buffer_size, *self.layout.command.values())

    def clear_line(self, line_num, start_x=0):
        with self.term.location(start_x, line_num):
            print(self.term.clear_eol())

    def move(self, x, y):
        print(self.term.move(x, y))

    def idle(self):
        self.draw_static()

    def draw_static(self):

        # prompt
        # if not self.prompt_in_use:
        #     self.clear_prompt()
        #     self.update_prompt_symbol(self.prompt)
        # self.term.move(0, self.data_start_line)

        # self.message(" ")
        # self.debug(" ")
        # top
        # self.temp_print("Log:", *self.layout.log.values())
        # self.temp_print("Command:", *self.layout.command.values())
        # self.temp_print(self.get_line(), 0, self.layout.log.y)
        # self.temp_print(self.get_line(), 0, self.layout.command.y)
        # self.command("")
        if self.use_separator_lines:
            self.temp_print(self.get_line(stroke="*"), *self.layout.debug.above().values())
            self.temp_print(self.get_line(), *self.layout.log.below().values())

    def get_line(self, width=None, stroke="-", reduce_by=None, use_arrowheads=True):
        width = self.width if width is None else width
        if reduce_by is not None:
            if type(reduce_by) is int:
                width -= reduce_by
            else:
                width -= len(reduce_by)
        if use_arrowheads:
            width -= 2
        return "<" + (stroke * width) + ">"


    def temp_print(self, msg, x, y, max_size=None):
        if max_size is not None:
            msg = utils.limit_size(msg, max_size)
        # # skip the log line
        # yy = y + 1
        # clear the line to its end
        with self.term.location(x, y):
            # print("@[{}, {}]: {}".format(x, y, msg))
            print("{}".format(msg))

    def message(self, msg):
        self.print_to_layout(msg, "Message", self.layout.message, do_clear=True, max_size=self.layout.message.w)

    def update_prompt_symbol(self, prompt):
        self.temp_print(prompt, *self.layout.command.values())
        coords = self.layout.command.x + len(prompt) + 1, self.layout.command.y
        return coords

    def debug(self, msg):
        self.print_to_layout(msg, "Debug", self.layout.debug, do_clear=True, max_size=self.layout.debug.w)

    def newline(self):
        pass

    # # printing funcs, add data clearing
    # def print_entries_enum(self, x_iter, entry_collection, at_most=None, additional_fields=None, print_newline=False):
    #     self.clear_data()
    #     with self.term.location(0, self.data_start_line):
    #         super().print_entries_enum(x_iter, entry_collection, at_most, additional_fields, print_newline)

    # def print_entries_contents(self, entries):
    #     self.clear_data()
    #     with self.term.location(0, self.data_start_line):
    #         entry_contents_str = "\n".join([self.get_entry_contents(entry) for entry in entries])
    #         self.print(entry_contents_str)

    # def print_enum(self, x_iter, at_most=None, additionals=None, header=None, preserve_col_idx=None):
    #     self.clear_data()
    #     with self.term.location(0, self.data_start_line):
    #         # Io.print_enum(self, x_iter, at_most, additionals)
    #         self.print(self.enum(x_iter))

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
        # self.clear_prompt()
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
                self.debug("Metakey: {}".format(name))
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
            # self.temp_print(res, x, y)
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
