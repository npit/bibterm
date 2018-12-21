import os

# check if s equals or is the start of opts or any of its elements
def matches(s, opts):
    if type(opts) == list:
        for c in opts:
            if matches(s, c):
                return True
        return False
    return s == opts or opts.startswith(s)


def get_index_list(inp):
    idxs = []
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
