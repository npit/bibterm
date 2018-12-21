import json
import utils
from fuzzywuzzy import process
from fuzzywuzzy import fuzz


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

    only_debug = False
    do_debug = False
    default_option_mark = "*"
    score_match_threshold = 50
    instance = None

    def set_only_debug(self, val):
        self.only_debug = val

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
        if self.only_debug and not self.do_debug:
            return
        print(msg)

    def fatal_error(self, msg):
        self.error(msg)
        exit(1)

    def error(self, msg):
        self.print("Error: " + msg)

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
        self.print("---------------")
        self.print(json.dumps(entry.get_pretty_dict(), indent=2))
        self.print("---------------")


# blessings ncurses for humans
class Blessings(Io):
    pass
    # def idle(self):
    #     print("Give command.")

    # def print(self, msg):
    #     print(msg)

    # def input(self, msg=""):
    #     return input(msg)

    # def search(self, query, candidates, at_most):
    #     return process.extract(query, candidates, limit=at_most)

    # def newline(self):
    #     print()
