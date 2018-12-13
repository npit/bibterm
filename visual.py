import json
import utils
from fuzzywuzzy import process


# base class to get and print stuff
def setup(conf):
    try:
        if conf.visual == "default":
            return Io()
        else:
            print("Undefined IO config:", conf.io)
            exit(1)
    except:
        print("Failed to read visual configuration.")
        exit(1)


class Io:
    default_option_mark = "*"
    def idle(self):
        print("Give command: ", end="")

    def list(self, content):
        pass

    def print(self, msg=""):
        print(msg)

    def error(self, msg):
        self.print(msg)
        exit(1)

    def input(self, msg="", options_str=None):
        default_idx = None
        if options_str is not None:
            opts = options_str.split()
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
            opt_print = " ".join(opt_print)
            msg += " " + opt_print + ": "

        while True:
            ans = input(msg)
            if options_str:
                # default option on empty input
                if not ans and default_idx is not None:
                    return opts[default_idx]
                # loop on invalid input
                if not utils.matches(ans, opts):
                    self.print("Valid options are: " + opt_print)
                    continue
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
        self.print(json.dumps(entry.get_pretty_dict(), indent=2))


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
