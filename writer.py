from os.path import join
from shutil import copyfile

import bibtexparser

import utils
from visual.instantiator import setup


def dict_to_raw_bibtex(entry_dict):
    """Convert an entry dict to a bibtex entry"""
    w = bibtexparser.bwriter.BibTexWriter()
    res = w.write(entry_dict)
    return res

class Writer:

    bib_path = None

    def __init__(self, conf):
        """
        Adds copied bibtex entry to bibtex file
        """
        self.conf = conf
        self.visual = setup(conf)
        try:
            self.bib_path = conf.get_user_settings()["bib_path"]
        except KeyError:
            self.visual.fatal_error("No bib path defined in the user settings!")

    # merge bib file to database
    def merge(self, entry_collection, other_collection):
        self.visual.print("Merging {}-sized collection:".format(len(other_collection.entries)))
        ids_to_insert = []
        ids_to_replace = []
        id_matches = []

        self.visual.print_entries_enum(other_collection.entries.values(), other_collection, at_most=20)

        for ID in other_collection.entries:
            ids_to_insert.append(ID)
            if ID in entry_collection.id_list:
                id_matches.append(ID)

        if id_matches:
            self.visual.print("{} duplicate ids (already exist in {})".format(len(id_matches), self.bib_path))
            self.visual.print_entries_enum([entry_collection.entries[ID] for ID in id_matches], entry_collection, at_most=20)
            # for ID in id_matches:
            #     entry = entry_collection.entries[ID]
            #     self.visual.print("{} {}".format(self.visual.ID_str(entry.ID, entry_collection.maxlen_id), self.visual.title_str(entry.title, entry_collection.maxlen_title)))

            what = self.visual.ask_user("Duplicates exist, what do?", "replace omit *abort")
            if utils.matches(what, "abort"):
                self.visual.print("Aborting.")
                exit(1)
            if utils.matches(what, "omit"):
                # omit them
                ids_to_insert = [i for i in ids_to_insert if i not in id_matches]
            if utils.matches(what, "replace"):
                ids_to_replace = id_matches
                ids_to_insert = [i for i in ids_to_insert if i not in ids_to_replace]

        if not ids_to_insert and not ids_to_replace:
            self.visual.print("Nothing left to merge.")
            return None
        # insert them
        if ids_to_insert:
            self.visual.print("Proceeding to insert {} entries:".format(len(ids_to_insert)))
            for i, ID in enumerate(ids_to_insert):
                entry = other_collection.entries[ID]
                strs = self.visual.gen_entry_enum_strings(entry, other_collection.maxlens(ids_to_insert), i + 1, len(ids_to_insert))
                self.visual.print("Inserting {} {} {}".format(*strs))
                entry_collection.create(entry)

        if ids_to_replace:
            self.visual.print("Proceeding to replace {} entries:".format(len(ids_to_replace)))
            for i, ID in enumerate(ids_to_replace):
                entry = other_collection.entries[ID]
                strs = self.visual.gen_entry_enum_strings(entry, other_collection, i + 1, len(ids_to_insert))
                self.visual.print("Inserting {} {} {}".format(*strs))
                entry_collection.replace(entry)
        return entry_collection

    def write(self, entry_collection):
        self.visual.log("Writing {} items to {}".format(len(entry_collection.bibtex_db.entries), self.bib_path))
        # first backup to a temporary file
        tmp_path = join(self.conf.get_tmp_dir(), "library.backup.bib")
        copyfile(self.bib_path, tmp_path)
        try:
            with open(self.bib_path, "w") as f:
                bibtexparser.dump(entry_collection.get_writable_db(), f)
        except Exception as ex:
            self.visual.error(f"Failed to update library file [{ex}]. Restoring previous version.")
            copyfile(tmp_path, self.bib_path)

    def write_confirm(self, entry_collection):
        what = self.visual.yes_no("Proceed to write?")
        if utils.matches(what, "yes"):
            self.write(entry_collection)
            self.visual.print("Wrote!")
        else:
            self.visual.print("Aborting.")

    @staticmethod
    def entries_to_bibtex_string(entries):
        """Make a bibtex db from input entries"""
        entries = [entries] if type(entries) != list else entries
        entries_string = []
        writer = bibtexparser.bwriter.BibTexWriter()
        for e in entries:
            wd = e.get_writable_dict()
            bt = writer._entry_to_bibtex(wd)
            entries_string.append(bt)
        entries_string = "\n".join(entries_string)
        return entries_string

