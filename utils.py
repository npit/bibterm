import time
from collections import namedtuple
from os.path import basename, join
from shutil import copyfile

import clipboard


class Backup:
    """Backup file manager"""
    def __init__(self, output_path, temp_dir):
        self.output_path = output_path
        self.backup_path = join(temp_dir, basename(output_path))
        copyfile(output_path, self.backup_path)

    def restore(self):
        copyfile(self.backup_path, self.output_path)


# datetime for timestamps
def datetime_str():
    return time.strftime("%d%m%y_%H%M%S")


# convert objetct / members to list
def listify(x):
    if type(x) not in (list, tuple):
        x = [x]
    if type(x[0]) not in (list, tuple):
        x = [[k] for k in x]
    return x

def get_single_index(inp):
    """ get a single numeric from input"""
    res = None
    try:
        res = int(inp)
    except:
        pass
    return res

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


def to_namedtuple(conf_dict, ntname="xxx"):
    keys = sorted(conf_dict.keys())
    conf = namedtuple(ntname, keys)(*[conf_dict[k] for k in keys])
    return conf


def is_index_list(inp):
    """Determine if the input has only slicable numeric list elements
    """
    inp = inp.strip()
    return len((inp)) > 0 and all([x in [" ", ":", "-"] or x.isdigit() for x in inp])


def is_valid_index_list(inp):
    if not is_index_list(inp):
        return False
    if ":" in inp:
        consequtive_colons = any([inp[i] == inp[i + 1] == ":" for i in range(len(inp) - 1)])
        if len(inp) == 1 or consequtive_colons:
            return False
    return True

def str_to_int(inp, default=None):
    """Cast string to integer"""
    try:
        return int(inp)
    except ValueError:
        return default

def handle_negative_index(idx, total):
    """Handle negative-valued indexes"""
    if idx is not None and idx < 0:
        idx = total + idx + 1
    return idx

def parse_slice(num, total_index_num):
    """Parse a string representing pythonic index slicing"""
    # allow pythonic slicing
    try:
        start, end = num.split(":")
    except ValueError:
        # only two-operand slices allowed
        return None
    start, end = str_to_int(start), str_to_int(end)
    if start is None and end is None:
        return None

    start = handle_negative_index(start, total_index_num)
    end = handle_negative_index(end, total_index_num)
    slice_idxs = expand_slice(start, end, total_index_num)
    return slice_idxs


def handle_string_index(num, total_index_num):
    """Function to map a string representation of indexes to list of ints"""

    # cast to integer
    try:
        num = int(num)
        # return a list to mantain uniform return type with potential slices
        return [handle_negative_index(num, total_index_num)]
    except ValueError:
        # attempt to parse a slice
        if ":" in num:
            return parse_slice(num, total_index_num)
        else:
            # invalid string
            return None
    return None


def get_index_list(inp, total_index_num, allow_slicing=True):
    """Convert a string slicable numeric list to list of integers
    """
    if type(inp) is str:
        # split to string list
        inp = inp.strip().split()
    idxs = []
    for i, num in enumerate(inp):
        if type(num) is str:
            # parse string representation of indexes / slice ranges
            cur_idx = handle_string_index(num, total_index_num)
            if cur_idx is None:
                # non-parsable item encountered
                return None
            idxs.extend(cur_idx)
        else:
            # numeric
            idxs.append(handle_negative_index(num, total_index_num))
    return idxs


def expand_slice(start, end, total):
    """Generate sequence of idxs by slice operands"""
    if end is None:
        return list(range(start, total))
    if start is None:
        return list(range(0, end + 1))
    if start == end:
        return [start]
    if start < end:
        return list(range(start, end + 1))
    if start > end:
        return expand_slice(start, None, total) + expand_slice(0, end, total)
    return None

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
