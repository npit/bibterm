import json
import utils
from fuzzywuzzy import process


# base class to get and print stuff
def setup(conf):
    try:
        if conf.visual == "default":
            return Io.get_instance(conf=conf)
        else:
            print("Undefined IO config:", conf.io)
            exit(1)
    except:
        print("Failed to read visual configuration.")
        exit(1)


class Io:

    default_option_mark = "*"
    instance = None

    def __init__(self, conf):
        self.do_debug = conf.debug

    def get_instance(conf=None):
        if conf is not None:
            Io.instance = Io(conf)
        return Io.instance

    def idle(self):
        print("Give command: ", end="")

    def list(self, content):
        pass

    def print(self, msg=""):
        print(msg)

    def error(self, msg):
        self.print(msg)
        exit(1)

    # func to show choices. Bang options are explicit and are not edited
    def input(self, msg="", options_str=None, check=True):
        default_idx = None
        if options_str is not None:
            opts = options_str.split()
            explicit_opts = [x[1:] for x in opts if x.startswith("#")]
            opts = [x for x in opts if not x.startswith("#")]

            default_idx = [i for i in range(len(opts)) if opts[i].startswith(self.default_option_mark)]
            if default_idx:
                if len(default_idx) > 1:
                    self.error("Multiple defaults:" + options_str)
                default_idx = default_idx[0]
                # remove asterisk from raw inputs
                opts[default_idx] = opts[default_idx][1:]

            opt_print = ["[{}]{}".format(x[0], x[1:]) for x in opts]
            if default_idx is not None:
                # add asterisk on print
                opt_print[default_idx] = self.default_option_mark + opt_print[default_idx]
            opt_print = " ".join(opt_print + explicit_opts)
            msg += " " + opt_print + ": "
        else:
            msg += ": "

        while True:
            ans = input(msg)
            if options_str:
                # default option on empty input
                if not ans and default_idx is not None:
                    return opts[default_idx]
                # loop on invalid input, if check
                if check:
                    if not utils.matches(ans, opts):
                        self.print("Valid options are: " + opt_print)
                        continue
            else:
                ans = ans.strip()
            # valid or no-option input
            return ans

    def search(self, query, candidates, atmost):
        return process.extract(query, candidates, limit=atmost)

    def newline(self):
        self.print()

    def title_str(self, title, maxlen_title):
        return "{:<{w}s}".format(title, w=maxlen_title)

    def ID_str(self, ID, maxlen_id):
        return "{:<{w}s}".format("\\cite{" + ID + "}", w=maxlen_id + 7)

    def num_str(self, num, maxnum):
        numpad = len(str(maxnum)) - len(str(num))
        return "[{}]{}".format(num, " " * numpad)

    # enumerate a collection with indexes
    def enum(self, x_iter):
        return ["{} {}".format(self.num_str(i+1, len(x_iter)), x_iter[i]) for i in range(len(x_iter))]

    def print_enum(self, x_iter):
        for s in self.enum(x_iter):
            self.print(s)


    def gen_entry_enum_strings(self, entry, maxlens, num, max_num=None):
        if max_num is None:
            max_num = maxlens[0]
        return (self.num_str(num, max_num), self.ID_str(entry.ID, maxlens[1]),
                self.title_str(entry.title, maxlens[2]))

    # produce enumeration strings
    def gen_entries_enum_strings(self, entries, maxlens):
        enum_str_list = []
        for i, entry in enumerate(entries):
            enum_str_list.append(self.gen_entry_enum_strings(entry, maxlens, i + 1))
        return enum_str_list

    def debug(self, msg):
        if self.do_debug:
            return
        self.print("debug:{}".format(msg))

    # print a list of entries
    def print_entries_enum(self, x_iter, entry_collection, at_most=None):
        if at_most and len(x_iter) > at_most:
            idxs_print = list(range(at_most - 1)) + [len(x_iter) - 1]
        else:
            idxs_print = list(range(len(x_iter)))

        if len(x_iter) != len(entry_collection.entries):
            # recompute max lengths
            maxlen_id = max([len(x.ID) for x in x_iter])
            maxlen_title = max([len(x.title) for x in x_iter])
            maxlens = len(x_iter), maxlen_id, maxlen_title
        else:
            maxlens = entry_collection.maxlens()

        strings = self.gen_entries_enum_strings(x_iter, maxlens)
        print_dots = True
        for i, tup in enumerate(strings):
            if i in idxs_print:
                self.print("{} {} {}".format(*tup))
            else:
                if print_dots:
                    self.print("...")
                    print_dots = False

    def print_entry_contents(self, entry):
        self.print("---------------")
        self.print(json.dumps(entry.get_pretty_dict(), indent=2))
        self.print("---------------")


# blessings ncurses for humans
class Blessings(Io):
    def idle(self):
        print("Give command.")

    def print(self, msg):
        print(msg)

    def input(self, msg=""):
        return input(msg)

    def search(self, query, candidates, atmost):
        return process.extract(query, candidates, limit=atmost)

    def newline(self):
        print()
