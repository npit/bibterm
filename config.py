from os.path import expanduser, join, exists, isfile, dirname
from os import makedirs
import json
import clipboard

"""
Read configuration of the underlying bibtex database
"""


# configuration file path
def get_conf_filepath():
    return join(expanduser("~"), ".config", "bib", "config.json")


# build configuration
def create_config():
    conf = {}
    # get path to bib file
    bib_filepath = input("Give path to bibliography file (you can copy/paste): ")
    # check it
    if not exists(bib_filepath):
        print("Specified path does not exist.")
        exit(1)
    if not isfile(bib_filepath):
        print("Specified path is not a file.")
        exit(1)
    # populate configuration
    conf["bib_path"] = bib_filepath
    return conf


def get_defaults(conf):
    # controls
    conf["controls"] = {"search": "/",
                        "list": "l",
                        "repeat": "r",
                        "quit": "q",
                        "history_show": "h",
                        "history_reset": "hr",
                        "history_jump": "hj",
                        "history_back": "hb",
                        "history_forward": "hf",
                        "save": "s",
                        "tag": "t"}

    conf["actions"] = ["merge", "inspect"]
    conf["visual"] = "default"
    conf["pdf_dir"] = join(dirname(conf.bib_path), "pdfs")
    return conf


def get_config():
    # backup copied data, in case we are adding an entry
    copied_data = clipboard.paste()
    initialized = False
    conf_filepath = get_conf_filepath()
    # check for existence of config file
    if not exists(conf_filepath):
        # if not existing, create it interactively
        print("Configuration file {} does not exist, creating.".format(conf_filepath))
        conf = create_config()
        initialized = True
        # write config file for addbib
        conf_dir = dirname(conf_filepath)
        if not exists(conf_dir):
            print("Creating configuration directory to {}".format(conf_dir))
            makedirs(dirname(conf_filepath))

        conf = get_defaults(conf)
        print("Writing configuration to {}".format(conf_filepath))
        with open(conf_filepath, "w") as f:
            json.dump(conf, f)
    else:
        # if it exists, just read it
        with open(conf_filepath, "r") as f:
            conf = json.load(f)
    conf["created_new"] = initialized
    # restore copied data
    clipboard.copy(copied_data)
    return conf
