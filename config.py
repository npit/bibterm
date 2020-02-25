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
from visual.instantiator import available_uis


class Config:
    """Configuration class"""
    conf_dict = None

    def __init__(self, conf_dict=None):
        if conf_dict is not None:
            self.conf_dict = conf_dict
        self.user_setting_keys = ["bibtex_getter", "bibtex_getter_params", "pdf_getter", "pdf_getter_params", "pdf_dir", "ui", "tmp_dir", "bib_path", "view_columns", "sort_column", "search_result_size", "list_result_size"]
        self.modified = False

    def get_visual(self):
        try:
            return self.get_user_setting('ui')
        except KeyError:
            return "ttables"

    def get_selection_commands(self):
        return self.conf_dict["selection_commands"]

    def get_controls(self):
        return self.conf_dict["controls"]

    def get_pdf_apis(self):
        self.get()["pdf_apis"]

    def get_bibtex_apis(self):
        self.get()["bibtex_apis"]

    def get_num_retrieved_bibtex(self):
        self.get()["num_retrieved_bibtex"]

    def get_view_columns(self):
        cols = self.get_user_setting('view_columns')
        cols = self.get_default_view_columns() if not cols else cols
        return cols

    def get_sort_column(self):
        cols = self.get_view_columns()
        scol = None
        try:
            scol = self.get_user_setting('sort_column')
        except KeyError:
            pass
        scol = self.get_default_sort_column() if not scol else scol
        scol = cols[0] if scol not in cols else scol
        return scol

    def update_dict(self, ddict):
        self.conf_dict = ddict

    def get_user_settings(self):
        return self.conf_dict["user_settings"]

    def get_user_setting(self, key):
        try:
            return self.get_user_settings()[key]
        except KeyError:
            return None

    def get_debug(self):
        return self.get()["debug"]

    def get_ui(self):
        return self.get_user_setting("ui")

    def get_tmp_dir(self):
        return self.get_user_settings()["tmp_dir"]

    def get_default_view_columns(self):
        return ["ID", "title"]

    def get_default_sort_column(self):
        return "ID"

    def get_search_result_size(self):
        try:
            return self.get_user_settings()["search_result_size"]
        except KeyError:
            return 10

    def get_list_result_size(self):
        try:
            return self.get_user_settings()["list_result_size"]
        except KeyError:
            return 30

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

    def save_if_modified(self, verify_write=True, called_explicitely=True):
        # collection
        modified_status = "*has been modified*" if self.modified else "has not been modified"
        if verify_write:
            # for explicit calls, do not ask for verification
            if called_explicitely:
                pass
            else:
                # if auto-called and not modified, do nothing
                if not self.modified:
                    return
                # else verify
                if not self.visual.yes_no("The configuration {}. Overwrite?".format(modified_status), default_yes=False):
                    return
        # write
        self.write(self.get())

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
        elif key == "sort_column":
            if value not in Entry.useful_keys:
                valid = False
                msg = f"Invalid sort column set: {value}. Available ones are {Entry.useful_keys}"
        elif key in ["search_result_size", "list_result_size"]:
            try:
                value = int(value)
                if value <= 0:
                    raise ValueError
            except ValueError:
                msg = f"Search / list result size has to be an integer"
                valid = False
        elif key == "ui":
            if value not in available_uis:
                msg = f"Ui {value} is undefined. Available ones are {available_uis}"
                valid = False
        else:
            # ???
            import ipdb; ipdb.set_trace()
        return key, value, valid, msg

    def update_user_setting(self, key, value):
        """Function to update a key-value user-level setting"""
        if key not in self.user_setting_keys:
            return False, f"Undefined user setting {key}"
        key, value, valid, errmsg = self.validate_setting(key, value)
        if not valid:
            return False, errmsg
        config = self.get()
        config["user_settings"][key] = value
        return True, ""

    def update_setting(self, key, value):
        """Function to update a program-level key-value setting"""
        config = self.get()
        config[key] = value

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

        conf["pdf_dir"] = join(dirname(conf["bib_path"]), "pdfs")
        conf["tmp_dir"] = "/tmp/bib/"

        # fill in key-value pairs like the example config belowbelow
        """
            "user_settings": {
                "bibtex_getter": "bibsonomy",
                "bibtex_getter_params": ["username", "passwd"],
                "pdf_getter": "scholar",
                "pdf_getter_params": "firefox",
                "pdf_dir": "/path/to/my/pdfs",
                "visual": "ttables",
                "tmp_dir": "/tmp/bib",
                "bib_path": "/path/to/library.bib",
                "view_columns": ["ID", "author", "title", "inserted"],
                "sort_column": "ID"
            },
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
