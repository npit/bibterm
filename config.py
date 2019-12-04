import json
from os import makedirs
from os.path import dirname, exists, expanduser, isfile, join

import clipboard

import utils


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
    browser_cmd = input("Give browser command: ")
    # populate configuration
    conf["bib_path"] = bib_filepath
    conf["browser"] = browser_cmd
    return conf


def get_defaults(conf):
    # controls
    conf["controls"] = {
        "search": "/",
        "down": "j",
        "get": "g",
        "up": "k",
        "list": "l",
        "check": "check",
        "clear": "",
        "unselect": "us",
        "delete": "del",
        "repeat": "r",
        "show": "sh",
        "quit": "q",
        "save": "sa",
        "cite": "c",
        "pdf_file": "fp",
        "pdf_search": "fs",
        "pdf_web": "fw",
        "pdf_open": "o",
        "history_show": "h",
        "history_reset": "hr",
        "history_jump": "hj",
        "history_back": "hb",
        "history_forward": "hf",
        "truncate": "tr",
        "tag": "ta",
    }

    # controls that can act on selection(s)
    conf["selection_commands"] = ["list", "delete", "cite", "tag", "pdf_file", "pdf_web", "pdf_open"]

    conf["pdf_search"] = {
        "gscholar": "https://scholar.google.com/scholar?hl=en&q=",
        "scihub": "https://sci-hub.tw", "scholarly":"",
        "bibsonomy": ["https://www.bibsonomy.org/search/", "username", "api_key"]}
    conf["actions"] = ["merge", "inspect"]
    conf["visual"] = "ttables"
    conf["pdf_dir"] = join(dirname(conf["bib_path"]), "pdfs")
    conf["user_settings"] = {}
    return conf


def get_config():
    # backup copied data, in case we are adding an entry
    copied_data = utils.paste(single_line=False)
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


def update_config(updlist):
    config = get_config()
    for bundle in updlist:
        curr_dict = config
        print("Setting update:", bundle)
        while len(bundle) > 2:
            key = bundle.pop(0)
            curr_dict = curr_dict[key]
        key, val = bundle
        curr_dict[key] = val
