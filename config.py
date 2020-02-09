"""
Configuration module
"""
import json
from os import makedirs
from os.path import dirname, exists, expanduser, isfile, join

import clipboard

import utils
from getters.getterFactory import GetterFactory
from reader import Entry


class Config:
    """Configuration class"""
    conf_dict = None

    def __init__(self, conf_dict=None):
        if conf_dict is not None:
            self.conf_dict = conf_dict

    def get_controls(self):
        return self.conf_dict["controls"]

    def update_dict(self, ddict):
        self.conf_dict = ddict

    def get_user_settings(self):
        return self.conf_dict["user_settings"]

    def get_debug(self):
        return self.get()["debug"]

    def get_visual(self):
        return self.get_user_settings()["visual"]

    def get_tmp_dir(self):
        return self.get_user_settings()["tmp_dir"]

    def get_default_view_columns(self):
        return ["ID", "title"]

    def get_pdf_dir(self):
        pdir = self.get_user_settings()["pdf_dir"]
        if pdir is None:
            pdir = join(dirname(self.get_user_settings()["bib_path"]), "pdfs")
        return pdir

    def write(self, conf, path=None):
        try:
            backup = utils.Backup(self.get_filepath(), join(self.get_tmp_dir()))
            with open(self.get_filepath(), "w") as f:
                json.dump(conf, f)
            return True, ""
        except Exception as ex:
            backup.restore()
            return False, str(ex)

    def validate_setting(self, key, value):
        """Validate setting values"""
        valid, msg = True, "OK"
        if key in "bibtex_getter pdf_getter".split():
            avail = GetterFactory.get_names()
            if value not in avail:
                valid = False
                msg = f"No getters named {value}. Available ones are {avail}"
        elif key == "view_columns":
            value = value.split()
            invalids = [v for v in value if v not in Entry.useful_keys]
            if invalids:
                valid = False
                msg = f"Invalid column(s) set: {invalids}. Available ones are {Entry.useful_keys}"
        return key, value, valid, msg

    def update_user_setting(self, key, value):
        if key not in self.get_user_settings().keys():
            return False, f"Undefined user setting {key}"
        key, value, valid, errmsg = self.validate_setting(key, value)
        if not valid:
            return False, errmsg
        config = self.get()
        config["user_settings"][key] = value
        return self.write(config)

    # configuration file path
    def get_filepath(self):
        return join(expanduser("~"), ".config", "bib", "config.json")

    # build configuration
    def create(self):
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
            "check": "ch",
            "clear": "",
            "unselect": "us",
            "delete": "del",
            "repeat": "r",
            "show": "sh",
            "merge": "m",
            "quit": "q",
            "save": "sa",
            "cite": "c",
            "cite-multi": "cm",
            "pdf_file": "fp",
            "debug": "deb",
            "pdf_search": "fs",
            "pdf_web": "fw",
            "pdf_open": "o",
            "history_show": "hs",
            "history_reset": "hr",
            "history_jump": "hj",
            "history_back": "hb",
            "history_log": "hl",
            "history_forward": "hf",
            "truncate": "tr",
            "settings": "se",
            "tag": "ta"
        }

        # controls that can act on selection(s)
        conf["selection_commands"] = ["list", "delete", "cite", "cite-multi", "tag", "pdf_file", "pdf_web", "pdf_open"]

        conf["pdf_apis"] = ["gscholar", "scihub", "bibsonomy"]
        conf["bibtex_apis"] = ["gscholar", "scholarly", "bibsonomy"]
        conf["doi_apis"] = ["crossref"]

        conf["actions"] = ["merge", "inspect"]
        conf["num_retrieved_bibtex"] = 5

        conf["visual"] = "ttables"
        conf["pdf_dir"] = join(dirname(conf["bib_path"]), "pdfs")
        conf["tmp_dir"] = "/tmp/bib/"

        # fill in key-value pairs like the example config belowbelow
        """
        "user_settings":{
            "bibtex_getter": "bibsonomy",
            "bibtex_getter_params": ["username", "api_key"],
            "pdf_getter": "scihub",
            "bib_path": "/home/myusername/papers/library.bib",
            "browser": "firefox"
        }
        """
        conf["user_settings"] = {}

        return conf

    def get(self):
        if self.conf_dict is not None:
            return self.conf_dict
        # backup copied data, in case we are adding an entry
        copied_data = utils.paste(single_line=False)
        initialized = False
        conf_filepath = self.get_filepath()
        # check for existence of config file
        if not exists(conf_filepath):
            # if not existing, create it interactively
            print("Configuration file {} does not exist, creating.".format(conf_filepath))
            conf = self.create_config()
            initialized = True
            # write config file for addbib
            conf_dir = dirname(conf_filepath)
            if not exists(conf_dir):
                print("Creating configuration directory to {}".format(conf_dir))
                makedirs(dirname(conf_filepath))

            conf = self.get_defaults(conf)
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
        self.conf_dict = conf
        return conf

    def get_namedtuple(self, conf_dict=None):
        if conf_dict is None:
            conf_dict = self.get()
        nt = utils.to_namedtuple(conf_dict, "conf")
        return nt
