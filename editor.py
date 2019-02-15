from visual import setup
import utils
import os

class Editor:

    def __init__(self, conf):
        self.conf = conf
        self.visual = setup(conf)
        self.collection_modified = False
        self.clear_cache()
        if conf.pdf_dir is None:
            self.pdf_dir = os.path.join(os.path.dirname(self.conf.bib_path), "pdfs")
        else:
            self.pdf_dir = conf.pdf_dir

    def clear_cache(self):
        self.cache = None
        self.do_apply_cache = None

    def get_raw_input(self, msg):
        self.cache = self.visual.ask_user(msg, multichar=True)
        return self.cache

    def get_input(self, msg):

        if self.cache is None:
            return self.get_raw_input(msg)

        # check hard Yes / No
        if self.do_apply_cache:
            return self.cache
        if not self.do_apply_cache:
            return self.get_raw_input(msg)

        # no hard setting exists, ask
        what = self.visual.ask_user("Insert existing input cache? {}".format(self.cache), "*yes Yes-all no No-all")

        # on hard selections, set variable and recurse
        if utils.matches(what, "Yes"):
            self.do_apply_cache = True
            return self.get_input(msg)
        if utils.matches(what, "No"):
            self.do_apply_cache = False
            return self.get_input(msg)

        # on soft selections, do the thing.
        if utils.matches(what, "yes"):
            return self.cache
        if utils.matches(what, "no"):
            return self.get_raw_input(msg)

    def set_file(self, entry, file_path=None):
        self.visual.log("About to insert pdf file to [{}]".format(entry.ID))
        if file_path is None:
            file_path = self.get_input("File path")
            while not os.path.exists(file_path) and self.visual.yes_no("No file is at that path. Re-enter?", default_yes=False):
                file_path = self.get_input("File path")
        if not file_path:
            self.visual.debug("Ignoring empty file path.")
            return None

        if self.make_canonic_pdf_name(file_path, entry):
            # fix and set canonic path
            pass
        else:
            # path already canonic
            entry.set_file(file_path)
        self.collection_modified = True
        return entry

    def tag(self, entry):
        self.visual.print("Inserting tag to [{}]".format(entry.ID))
        # self.visual.print("Inserting tag to existing entry contents:")
        # self.visual.print_entry_contents(entry)
        existing_tags = entry.keywords if entry.keywords else []

        tags = self.get_input("Insert tags to the existing {} ".format(existing_tags)).split()
        if not tags:
            self.visual.print("Nothing entered.")
            return None
        tags = list(set(existing_tags + tags))
        entry.set_keywords(tags)

        # self.visual.print("Entry is now:")
        # self.visual.print_entry_contents(entry)
        self.collection_modified = True
        return entry

    def open(self, entry):
        if not entry.has_file():
            self.visual.error("No file field in entry {}".format(entry.ID))
            return False
        file_path = utils.fix_file_path(entry.file, self.pdf_dir)
        if os.path.exists(file_path):
            self.make_canonic_pdf_name(file_path, entry)
            self.visual.print("Opening: {}".format(file_path))
            os.system("/usr/bin/xdg-open '{}'".format(file_path))
        else:
            self.visual.error("Entry file path does not exist: {}".format(file_path))
        return True


    def fix_file_path(path, pdf_dir=None):
        if path.endswith(":pdf"):
            path = path[:-4]
        if path.startswith(":home"):
            path = "/" + path[1:]
        if pdf_dir is not None and not os.path.isabs(path):
            if not path.startswith("/home"):
                path = os.path.join(pdf_dir, path)
        return path

    def get_entry_canonic_pdf_path(self, entry):
        return os.path.join(self.pdf_dir, entry.ID + ".pdf")

    def make_canonic_pdf_name(self, file_path, entry):
        proper_path = self.get_entry_canonic_pdf_path(entry)
        if proper_path != file_path:
            if self.visual.yes_no("File path {} differs from the proper one: {} -- rename & move?".format(file_path, proper_path)):
                breakpoint()
                os.rename(file_path, proper_path)
                self.visual.log("Renamed {} to {} -- rename?".format(file_path, proper_path))
                self.set_file(entry, proper_path)
                return True
        return False
