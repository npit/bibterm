import utils
from visual import setup
import bibtexparser


class Writer:

    bib_path = None

    def __init__(self, conf):
        """
        Adds copied bibtex entry to bibtex file
        """
        self.conf = conf
        self.bib_path = conf.bib_path
        self.visual = setup(conf)

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

            what = self.visual.input("Duplicates exist, what do?", "replace omit *abort")
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
        self.visual.print("Proceeding to insert {} entries:".format(len(ids_to_insert)))
        for i, ID in enumerate(ids_to_insert):
            entry = other_collection.entries[ID]
            strs = self.visual.gen_entry_enum_strings(entry, other_collection.maxlens(ids_to_insert), i + 1, len(ids_to_insert))
            self.visual.print("Inserting {} {} {}".format(*strs))
            entry_collection.create(entry)

        self.visual.print("Proceeding to replace {} entries:".format(len(ids_to_replace)))
        for i, ID in enumerate(ids_to_replace):
            entry = other_collection.entries[ID]
            strs = self.visual.gen_entry_enum_strings(entry, other_collection, i + 1, len(ids_to_insert))
            self.visual.print("Inserting {} {} {}".format(*strs))
            entry_collection.replace(entry)
        return entry_collection

    def write(self, entry_collection):
        self.visual.print("Writing {} items to {}".format(len(entry_collection.bibtex_db.entries), self.bib_path))
        with open(self.bib_path, "w") as f:
            bibtexparser.dump(entry_collection.get_writable_db(), f)

    def write_confirm(self, entry_collection):
        what = self.visual.input("Proceed to write?", "*yes no")
        if utils.matches(what, "yes"):
            self.write(entry_collection)
            self.visual.print("Wrote!")
        else:
            self.visual.print("Aborting.")
