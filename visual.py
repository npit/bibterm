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
    def idle(self):
        print("Give command: ", end="")

    def list(self, content):
        pass

    def print(self, msg):
        print(msg)

    def input(self,msg=""):
        return input(msg)

    def search(self, query, candidates, atmost):
        return process.extract(query, candidates, limit=atmost)

    def newline(self):
        print()

    def title_str(self, title, entry_collection):
        return "{:<{w}s}".format(title, w=entry_collection.maxlen_title)

    def ID_str(self, ID, entry_collection):
        return  "{:<{w}s}".format("\cite{" + ID + "}", w=entry_collection.maxlen_id+7)

    def num_str(self, num, maxnum):
        numpad = len(str(maxnum)) - len(str(num))
        return "[{}]{}".format(num, " "*numpad)

    def gen_entry_enum_strings(self, entry, entry_collection, num, max_num=100):
            return (self.num_str(num, max_num),
                              self.ID_str(entry.ID, entry_collection),
                              self.title_str(entry.title, entry_collection))

    # produce enumeration strings
    def gen_entries_enum_strings(self, entries, entry_collection):
        enum_str_list = []
        for i, entry in enumerate(entries):
            enum_str_list.append(self.gen_entry_enum_strings(entry, entry_collection, i + 1, len(entries)))
        return enum_str_list

    # print a list of entries
    def print_entry_enum(self, x_iter, entry_collection, at_most=None):

        if at_most and len(x_iter) > at_most:
            idxs_suspend = list(range(at_most - 1)) + [len(x_iter) - 1]
        else:
            idxs_suspend = []

        strings = self.gen_entries_enum_strings(x_iter, entry_collection)
        for i, tup in enumerate(strings):
            if i in idxs_suspend:
                continue
            self.print("{} {} {}".format(*tup))




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

