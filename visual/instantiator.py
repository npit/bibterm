from visual.blessed import Blessed
from visual.io import Io
from visual.termtables import TermTables


# base class to get and print stuff
def setup(config):
    visual_name = config.get_visual()
    if visual_name == Io.name:
        return Io.get_instance(config)
    elif visual_name == Blessed.name:
        return Blessed.get_instance(config)
    elif visual_name == TermTables.name:
        return TermTables.get_instance(config)
    else:
        print("Undefined ui config:", visual_name)
        exit(1)
