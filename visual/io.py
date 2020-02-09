import json
from itertools import combinations

import utils


class Io:
    name = "default"

    only_debug = False
    do_debug = False
    default_option_mark = "*"
    instance = None
    clear_size = 100
    prompt = ">"
    handles_max_results = None

    does_incremental_search = False
    search_time_delta = 0

    log_history = []

    def set_only_debug(self, val):
        self.only_debug = val

    def __init__(self, conf):
        self.do_debug = conf.get_debug()
        self.handles_max_results = True
        self.conf = conf

    @staticmethod
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
        self.log_history.append(msg)
        self.print(msg)

    def message(self, msg):
        self.print(msg)

    def error(self, msg):
        self.print("(!) {}".format(msg))

    def receive_command(self):
        return self.ask_user()

    def receive_search(self):
        return True, self.ask_user("Search:")

    # shortcut for looped information printing
    def print_loop(self, iterable_items, msg="", lambda_item=None, print_func=None, condition=None):
        if print_func is None:
            print_func = self.print
        idx = 0
        for item in iterable_items:
            if condition is not None:
                if not condition(item):
                    continue
            item_str = lambda_item(item) if lambda_item is not None else item
            print_func("{}/{} : {} {}".format(idx+1, len(iterable_items), item_str, msg))
            yield item
            idx += 1

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

    def user_multifilter(self, collection, header, reference=None, print_func=None, preserve_col_idx=None, message=None):
        """Filtering function by user index selection. Reference can be used to keep track of input items"""
        if reference is None:
            reference = list(range(len(collection)))
        if print_func is None:
            print_func = self.print_enum

        cur_reference, cur_collection = reference, collection
        while True:
            print_func(cur_collection, header=header, preserve_col_idx=preserve_col_idx)
            prompt = "{}Enter numeric indexes to modify the list, q to select none, or ENTER to proceed".format(message + ". " if message is not None else "")
            idxs = None
            while True:
                str_inp = self.ask_user(prompt)
                if str_inp == "q":
                    return [], []
                idxs = utils.get_index_list(str_inp, len(cur_collection))
                if idxs is None:
                    self.error("Invalid input: [{}], please read the instructions.".format(str_inp))
                    continue
                break
            if idxs:
                # subset was selected
                sel = sorted(set(idxs))
                cur_collection = [cur_collection[i-1] for i in idxs]
                cur_reference = [cur_reference[i-1] for i in idxs]
                # return immediately for single-selections
                if len(cur_collection) == 1:
                    return cur_collection, cur_reference

                print_func(cur_collection, header=header, preserve_col_idx=preserve_col_idx)
                # confirm for larger ones
                if self.ask_user("Keep these?", "*yes no(reset)") == "yes":
                    return cur_collection, cur_reference
                else:
                    # no subset was selected (return original collection)
                    cur_collection = collection
                    cur_reference = reference
            else:
                return collection, reference

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
    def gen_entries_strings(self, entries, cols):
        # get listable elements from the entry based on the config
        # collect data
        data = []
        for col in cols:
            # get column data
            col_data = [x.get_value(col, postproc=True) for x in entries]
            data.append(col_data)
            # col_maxlen = max([len(x) for x in col_data])

        # maxlen_id = max([len(x.ID) for x in entries])
        # maxlen_title = max([len(x.title) for x in entries])
        # maxlens = len(entries), maxlen_id, maxlen_title

        # enum_str_list = []
        # for i, entry in enumerate(entries):
        #     st = self.gen_entry_strings(entry, maxlens)
        #     enum_str_list.append(self.gen_entry_strings(entry, maxlens))
        data = list(zip(*data))
        return data

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
