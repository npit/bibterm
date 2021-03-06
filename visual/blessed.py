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
                self.layout.data.h -= 1

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
        self.commands = conf.get_controls()
        self.selection_commands = conf.get_selection_commands()

        # threading lock
        self.access_lock = threading.Lock()
        self.has_realtime_input = True

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

    def conditional_clear_selection(self, command):
        """Clear the selection cache on selecton-unrelated commands
        """
        if not self.selection_cache:
            return
        if command not in self.selection_commands:
            self.selection_cache = ""
            self.debug("Cleared selection")

    def submit_command(self, input_str, command_name):
        """Receive a fully-fledged command"""
        self.message(f"Executing command: {command_name}")
        self.clear_data()
        self.command(input_str)
        self.message(command_name)

    def submit_partial_input(self, input_str, candidate_commands):
        """Receive a fully-fledged command"""
        self.clear_data()
        self.command(input_str)
        self.message("Candidate commands: {}".format(",".join(candidate_commands)))

    def receive_command(self):
        x, y = self.layout.command.values()
        starting_x = 2
        x += starting_x
        done = False
        info_msg = ""

        inp = self.selection_cache

        # while not done:
        command = ""
        # input
        new_inp = self.input_multichar(starting_x, y, single_char=True, initial_entry=inp)
        # esc
        if new_inp is None:
            self.selection_cache = ""
            self.prompt_in_use = False
            command = None
            # break
        # enter
        if new_inp == inp:
            self.selection_cache = ""
            self.prompt_in_use = False
            command = inp
            # break
        # del to empty
        if not new_inp:
            self.selection_cache = ""
            self.prompt_in_use = False
            # break
        inp = new_inp

        self.debug("Sel. cache: [{}]".format(self.selection_cache))

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

    def input_singlechar(self, evaluate_sequences=True, initial_entry=None):
        """Get single-character entries
        Returns:
        res -- The entry string
        concluded -- whether a finalizing key was pressed
        """
        # return self.input_multichar(2, 0, single_char=True, initial_entry=initial_entry)
        res = initial_entry if initial_entry is not None else ""
        concluded = False
        # get key input
        key = self.get_raw_input()
        if self.get_metakey(key):
            # metakey handling
            name, func = self.get_metakey(key)
            self.debug("Metakey: {}".format(name))
            res += func(key)
        elif key.is_sequence:
            # blessed sequence key
            if key.name == "KEY_DELETE":
                if len(res) > 0:
                    res = res[:-1]
            if key.name == "KEY_ENTER":
                # on enter, we're done
                concluded = True
            if key.name == "KEY_ESCAPE":
                # on escape, return nothing
                res = ""
                concluded = True
        else:
            # regular input
            res += key
        return res, concluded

    def input_multichar(self, x, y, single_char=False, initial_entry=None):
        """Get multi-character entries, terminating with RET or ESC
        """
        res = initial_entry
        while True:
            res, concluded = self.input_singlechar(initial_entry=res)
            self.temp_print(res, x, y)
            if concluded:
                break
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
