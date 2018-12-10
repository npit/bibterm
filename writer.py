import clipboard
from os.path import exists
from visual import setup
import bibtexparser


class BibWriter:

    bib_path = None

    def __init__(self, conf, entry_collection=None):
        """
        Adds copied bibtex entry to bibtex file
        """
        self.conf = conf
        self.bib_path = conf.bib_path
        self.visual = setup(conf)

    # fetch citation id from bibtex item
    def get_id(self, content):
        try:
            # get the parser, parse the string
            content = bibtexparser.loads(content)
            # get ID, copy latex citation command
            b_id = content.entries[0]["ID"]
            citation_command = "\\cite{}".format("{" + b_id + "}")
            clipboard.copy(citation_command)
            print("Copied citation command: {} to clipboard.".format(citation_command))
        except:
            print("Failed to parse citation key.")

    # add clipboard contents to bib file
    def add(self):
        copied_data = clipboard.paste()
        print("Library:", self.bib_path)

        if not exists(self.bib_path):
            print("Warning: bib file is empty.")

        with open(self.bib_path, "a") as f:
            print("Adding content to library:")
            print("------------------------")
            print(copied_data)
            print("------------------------")
            if self.created_new:
                res = input("Continue? Y/n")
                if res.lower() == "n":
                    print("Aborting.")
                    exit(1)
            f.write("\n")
            f.write(copied_data)
            f.write("\n")
            print("Added.")
            self.get_id(copied_data)

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
            self.visual.print("There are {} duplicate ids:".format(len(id_matches)))
            for ID in id_matches:
                entry = entry_collection.entries[ID]
                self.visual.print("{} {}".format(self.visual.ID_str(entry.ID, entry_collection), self.visual.title_str(entry.title, entry_collection)))

            what = self.visual.input("[R]eplace, [o]mit, [a]bort? ").lower()

            if what == "a":
                self.visual.print("Aborting.")
                exit(1)
            if what == "o":
                # omit them
                ids_to_insert = [i for i in ids_to_insert if i not in id_matches]
            if what == "r":
                ids_to_replace = id_matches
                ids_to_insert = [i for i in ids_to_insert if i not in ids_to_replace]

        if not ids_to_insert and not ids_to_replace:
            self.visual.print("Nothing left to merge.")
            return
        # insert them
        self.visual.print("Proceeding to insert {} entries:".format(len(ids_to_insert)))
        for i, ID in enumerate(ids_to_insert):
            entry = other_collection.entries[ID]
            strs = self.visual.gen_entry_enum_strings(entry, other_collection, i + 1, len(ids_to_insert))
            self.visual.print("Inserting {} {} {}".format(*strs))
            entry_collection.insert(entry)

        self.visual.print("Proceeding to replace {} entries:".format(len(ids_to_replace)))
        for i, ID in enumerate(ids_to_replace):
            entry = other_collection.entries[ID]
            strs = self.visual.gen_entry_enum_strings(entry, other_collection, i + 1, len(ids_to_insert))
            self.visual.print("Inserting {} {} {}".format(*strs))
            entry_collection.replace(entry)
        

        # what = self.visual.input("Inspect udpated collection? *[y]es / [n]o: ")
        # if not what or what == "y":
        #     runner = Runner(self.conf, entry_collection=self.entry_collection)
        #     runner.loop()
        # else:
        #     self.visual.print_entry_enum(self.entry_collection.entries.values(), self.entry_collection)
        # write results
        return entry_collection

    def write(self, entry_collection):
        self.visual.print("Overwriting changes to {}".format(self.bib_path))
        with open(self.bib_path, "w") as f:
            bibtexparser.dump(entry_collection.get_writable_db(), f)
