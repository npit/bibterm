import os
from collections import namedtuple


# check if s equals or is the start of opts or any of its elements
def matches(partial, full):
    if type(full) == list:
        for c in full:
            if matches(c, full):
                return True
        return False
    if not partial:
        return False
    return (partial == full or full.startswith(partial))


def to_namedtuple(conf_dict, ntname):
    keys = sorted(conf_dict.keys())
    conf = namedtuple(ntname, keys)(*[conf_dict[k] for k in keys])
    return conf


def is_index_list(inp):
    """Determine if the input has only slicable numeric list elements
    """
    return all([x in [" ", ":"] or x.isdigit() for x in inp])


def get_index_list(inp, total_index_num, allow_slicing=True):
    """Convert a string slicable numeric list to list of integers
    """

    idxs = []
    # allow pythonic slicing
    if allow_slicing and ":" in inp:
        # make sure it's whitespace surrounded
        inp = inp.replace(":", " : ")
        inp = inp.strip().split()
        res = []
        # errors
        consequtive_colons = any([inp[i] == inp[i + 1] == ":" for i in range(len(inp) - 1)])
        if len(inp) == 1 or consequtive_colons:
            return None
        for i, x in enumerate(inp):
            if x == ":":
                if i == 0:
                    prev_element = 1
                    next_element = int(inp[i + 1])
                elif i == len(inp) - 1:
                    prev_element = int(inp[i - 1])
                    next_element = total_index_num
                else:
                    prev_element = int(inp[i - 1])
                    next_element = int(inp[i + 1])

                if next_element > total_index_num:
                    next_element = total_index_num

                # beginning of sequence
                res.extend(map(str, range(prev_element, next_element + 1)))
        inp = res

    if type(inp) == str:
        inp = inp.strip().split()
    for x in inp:
        x = str_to_int(x)
        if x is None:
            return None
        idxs.append(x)
    return idxs


def str_to_int(inp, default=None):
    try:
        return int(inp)
    except:
        return default


def has_none(inp):
    return inp is None or any([x is None for x in inp])


def fix_file_path(path, pdf_dir=None):
    if path.endswith(":pdf"):
        path = path[:-4]
    if path.startswith(":home"):
        path = "/" + path[1:]
    if pdf_dir is not None:
        if not path.startswith("/home"):
            path = os.path.join(pdf_dir, path)
    return path


# debug with statement for visual
class OnlyDebug:
    def __init__(self, visual):
        self.visual = visual

    def __enter__(self):
        self.visual.set_only_debug(True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.visual.set_only_debug(False)
