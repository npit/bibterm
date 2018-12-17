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
    try:
        if type(inp) == str:
            inp = inp.strip().split()
        for x in inp:
            idxs.append(int(x))
        return idxs
    except:
        return None
