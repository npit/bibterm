import re
import string
from os import listdir, remove, rename, system
from os.path import basename, dirname, exists, isabs, isdir, join, splitext

import utils
from getters.getter import Getter
from visual.instantiator import setup


class Editor:

    def __init__(self, conf):
        self.conf = conf
        self.visual = setup(conf)
        self.collection_modified = False
        self.clear_cache()
        if conf.pdf_dir is None:
            self.pdf_dir = join(dirname(self.conf.user_settings.bib_path), "pdfs")
        else:
            self.pdf_dir = conf.pdf_dir

    def check_pdf_naming_consistency(self, entry_collection):
        # check for missing pdfs
        missing_pdfs = [x for x in entry_collection.entries.values() if x.has_file() and not exists(x.file)]
        self.visual.error("Missing pdfs for {} entries".format(len(missing_pdfs)))
        existing_pdfs = [x for x in entry_collection.entries.values() if x not in missing_pdfs]

        # check for existing pdf names
        self.visual.log("Checking assigned pdf naming consistency.")
        non_canonics = [x for x in  existing_pdfs if not self.check_entry_canonic_pdf_path(x)]
        for entry in self.visual.print_loop(non_canonics, lambda_item=lambda x: "{}: {}".format(x.ID, x.file)):
            proper_path = join(self.pdf_dir, entry.file)
            entry_dir, entry_file = dirname(entry.file), basename(entry.file)
            if entry.file == proper_path:
                # set only leaf filename to the entry
                entry.file = entry.get_canonic_filename()
                self.visual.log("Setting leaf-only file entry")
                entry_collection.set_modified()
            else:
                self.make_canonic_pdf_name(entry.file, entry)
                self.visual.log("Making canonical path")
                entry_collection.set_modified()

        # check for unmatched pdfs in the pdf folder
        self.visual.log("Checking for dangling pdfs.")
        unmatched = []
        for fname in listdir(self.pdf_dir):
            fpath = join(self.pdf_dir, fname)
            if not entry_collection.pdf_path_exists(fpath):
                # attempt to assign
                candidate_id = splitext(fname)[0]
                if  candidate_id in entry_collection.id_list:
                    self.visual.log("Assigned dangling {} to matching id {}.".format(fname, candidate_id))
                    entry_collection.entries[candidate_id].set_file(fpath)
                    entry_collection.set_modified()
                else:
                    unmatched.append(fpath)
        if unmatched:
            self.visual.message("Pdfs in {} not matched to any entry:".format(self.pdf_dir))
            self.visual.print_enum(unmatched, at_most=30, header=["pdf path"])
            sel = self.visual.ask_user("What to do about them?", "delete move write-list search-collection *nothing")
            if utils.matches(sel, "delete"):
                for fpath in unmatched:
                    remove(fpath)
                self.visual.message("Deleted.")
            elif utils.matches(sel, "move"):
                move_dir = self.visual.ask_user("Directory to move pdfs to:")
                while not (exists(move_dir) and is_dir(move_dir)):
                    if not move_dir:
                        self.visual.message("Aborting.")
                        return
                    self.visual.message("Not a valid directory: {}".format(move_dir))
                    for fpath in unmatched:
                        os.rename(fpath, join(move_dir, basename(fpath)))
                    self.visual.message("Moved.")
            elif utils.matches(sel, "write-list"):
                write_file = self.visual.ask_user("Write to what file?")
                while not (exists(write_file)):
                    if not write_file:
                        self.visual.message("Aborting.")
                        return
                    self.visual.message("Not a valid file: {}".format(write_file))
                    with open(write_file, "w") as f:
                        f.write("\n".join(unmatched))
                    self.visual.message("Wrote.")
            elif utils.matches(sel, "search-collection"):
                all_titles = entry_collection.title_list
                all_authors = list(set([auth for ent in entry_collection.entries.values() for auth in ent.author]))
                for i, upath in enumerate(unmatched):
                    filename = upath.split(os.sep)[-1][:-4]
                    self.visual.message("Looking for candidate entries for dangling pdf {}/{}: [{}]".format(i+1, len(unmatched), filename))
                    filename = re.sub("[{}]".format(string.punctuation), " ", filename)
                    # titles
                    res = self.visual.search(filename, all_titles, 5)
                    ids = [entry_collection.title2id[r[0][0]] for r in res]
                    titles = [r[0][0] for r in res]
                    results = list(zip(ids, titles))

                    # authors
                    res = self.visual.search(filename, all_authors, 5)
                    ids = list(set([ID for r in res for ID in entry_collection.author2id[r[0][0]]]))
                    titles = [entry_collection.entries[ID].title for ID in ids]
                    results += list(zip(ids, titles))

                    while True:
                        result, _ = self.visual.user_multifilter(results, header='id title'.split(), preserve_col_idx=[0])
                        if len(result) > 1:
                            self.visual.error("Select at most one element, dude.")
                            continue
                        break
                    if not result:
                        if self.visual.yes_no("Continue to next pdf?"):
                            continue
                        break
                    entry = entry_collection.entries[result[0][0]]
                    self.visual.print_entry_contents(entry)
                    if self.visual.yes_no("Insert {} to the entry?".format(upath)):
                        if entry.has_file():
                            if not self.visual.yes_no("Overwrite existing file {} ?".format(entry.file)):
                                continue
                        self.make_canonic_pdf_name(entry, upath)
                        entry_collection.set_modified()


    def check_missing_fields(self, entry_collection):
        self.visual.message("Checking for missing entry fields.")
        missing_per_entry, missing_per_field = entry_collection.check_for_missing_fields()
        if missing_per_entry:
            self.visual.message("Missing {} distinct fields from {} entries".format(len(missing_per_field), len(missing_per_entry)))
            if self.visual.yes_no("Search bibtexs to complete the entries?"):
                gt = Getter(self.conf)
                for eidx, (entryid, fields) in enumerate(missing_per_entry.items()):
                    # search by title
                    title = entry_collection.entries[entryid].title
                    results = gt.get_web_bibtex(title)
                    self.visual.print_entry_contents(entry_collection.entries[entryid])
                    for field in fields:
                        useful_results = []
                        for res in results:
                            if field in res:
                                useful_results.append(res)
                        # show results for the entry that contain the missing field
                        self.visual.print("Entry {}/{} - [{}]: [{}], missing field: {}, {} candidates with such information.".format(eidx, len(missing_per_entry), entryid, title, field, len(useful_results)))
                        if not useful_results:
                            continue
                        while True:
                            listcols = [list(u.items()) for u in useful_results]
                            _, selected_ids = self.visual.user_multifilter(listcols, header='keys attributes'.split(), print_func=self.visual.print_multiline_items)
                            if len(selected_ids) > 1:
                                self.visual.error("Selected: {}, need to select at most one candidate.".format(selected_ids))
                                continue
                            break
                        if not selected_ids:
                            if not self.visual.yes_no("Continue?"):
                                return
                            continue

                        result = [useful_results[i] for i in selected_ids][0]
                        self.visual.print("Setting entry field [{}] to [{}]".format(field, result[field]))
                        entry_collection.entries[entryid].set_dict_value(field, result[field])
                        entry_collection.set_modified()


    def check_consistency(self, entry_collection):
        self.check_pdf_naming_consistency(entry_collection)
        self.check_missing_fields(entry_collection)

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
        if file_path is None:
            file_path = self.get_input("File path")
            while not exists(file_path) and self.visual.yes_no("No file is at that path. Re-enter?", default_yes=False):
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
        file_path = self.fix_file_path(entry.file, self.pdf_dir)
        if exists(file_path):
            if self.make_canonic_pdf_name(file_path, entry):
                file_path = self.get_entry_canonic_pdf_path(entry)
            self.visual.print("Opening: {}".format(file_path))
            system("/usr/bin/xdg-open '{}'".format(file_path))
        else:
            self.visual.error("Entry file path does not exist: {}".format(file_path))
        return True

    def fix_file_path(self, path, pdf_dir=None):
        if path.endswith(":pdf"):
            path = path[:-4]
        if path.startswith(":home"):
            path = "/" + path[1:]
        if pdf_dir is not None and not isabs(path):
            if not path.startswith("/home"):
                path = join(pdf_dir, path)
        return path

    def get_entry_canonic_pdf_path(self, entry):
        return join(self.pdf_dir, entry.get_canonic_filename())

    def check_entry_canonic_pdf_path(self, entry):
        if not entry.has_file():
            return True
        # return join(self.pdf_dir, entry.get_canonic_filename()) == entry.file
        return (entry.get_canonic_filename() == entry.file) and exists(join(self.pdf_dir, entry.file))

    def make_canonic_pdf_name(self, file_path, entry, do_ask=True):
        proper_path = self.get_entry_canonic_pdf_path(entry)
        if proper_path != file_path:
            if do_ask:
                if not self.visual.yes_no("File path [{}] differs from the proper one: [{}] -- rename & move?".format(file_path, proper_path)):
                    return False
            rename(file_path, proper_path)
            self.visual.log("Renamed {} to {} -- rename?".format(file_path, proper_path))
            self.set_file(entry, proper_path)
            return True
        return False
