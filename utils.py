from collections import namedtuple
import clipboard


# paste handler
def paste(single_line=True):
    pasted_content = clipboard.paste()
    if single_line:
        # remove newlines
        pasted_content = pasted_content.replace("\n", " ")
    return pasted_content


def limit_size(msg, max_size, trunc_symbol="..."):
    """Apply max-length truncation to a string message
    """
    if len(msg) > max_size:
        msg = msg[:max_size - len(trunc_symbol)] + trunc_symbol
    return msg


# check if s equals or is the start of opts or any of its elements
def matches(partial, full):
    if type(full) == list:
        for c in full:
            if matches(partial, c):
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


def is_valid_index_list(inp):
    if not is_index_list(inp):
        return False
    if ":" in inp:
        consequtive_colons = any([inp[i] == inp[i + 1] == ":" for i in range(len(inp) - 1)])
        if len(inp) == 1 or consequtive_colons:
            return False
    return True


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
        if not is_valid_index_list(inp):
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


# debug with statement for visual
class OnlyDebug:
    def __init__(self, visual):
        self.visual = visual

    def __enter__(self):
        self.visual.set_only_debug(True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.visual.set_only_debug(False)
