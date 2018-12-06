import clipboard
import reader
from os.path import exists
from runner import EntryCollection
from reader import Reader
from visual import setup
import bibtexparser
from runner import Runner


class Adder:
    bib_filepath = None

    def __init__(self, conf):
        """
        Adds copied bibtex entry to bibtex file
        """
        self.conf = conf
        self.bib_filepath = conf.bib_path
        self.created_new = conf.created_new
        # read the bib database
        rdr = Reader(conf)
        rdr.read()
        self.entry_collection = EntryCollection(rdr.get_content())

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
        print("Library:", self.bib_filepath)

        if not exists(self.bib_filepath):
            print("Warning: bib file is empty.")

        with open(self.bib_filepath, "a") as f:
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
    def merge(self, other_bib_filepath):
        if not exists(other_bib_filepath):
            print("Cannot find bib file to merge at {}".format(other_bib_filepath))
        rdr = reader.Reader(self.conf)
        rdr.bib_path = other_bib_filepath
        rdr.read()
        other_collection = EntryCollection(rdr.get_content())
        ids_to_insert = []
        id_matches = []
        title_matches = []

        self.visual.print_entry_enum(other_collection.entries.values(), other_collection, at_most=10)

        for ID in other_collection.entries:
            ids_to_insert.append(ID)
            if ID in self.entry_collection.id_list:
                id_matches.append(ID)
            if other_collection.entries[ID].title.lower() in self.entry_collection.title_list:
                title_matches.append(ID)

        if id_matches:
            self.visual.print("There are {} duplicate ids:".format(len(id_matches)))
            for ID in id_matches:
                entry = self.entry_collection.entries[ID]
                self.visual.print("{} {}".format(self.visual.ID_str(entry.ID, self.entry_collection), self.visual.title_str(entry.title, self.entry_collection)))

            # what = self.visual.input("[R]eplace, [o]mit, [a]bort? ")
            what='o'

            if what == "a":
                self.visual.print("Aborting.")
                exit(1)
            if what == "o":
                # omit them
                ids_to_insert = [i for i in ids_to_insert if i not in id_matches]
                # also remove corresponding titles from the title match list
                title_matches = [i for i in title_matches if i not in id_matches]

        if title_matches:
            self.visual.print("There are {} duplicate (remaining) titles:".format(len(title_matches)))
            for ID in title_matches:
                title = other_collection.entries[ID].title.lower()
                entry = self.entry_collection.entries[self.entry_collection.title2id[title]]
                self.visual.print("{} {}".format(self.visual.ID_str(entry.ID, self.entry_collection), self.visual.title_str(entry.title, self.entry_collection)))
            # what = self.visual.input("[R]eplace, [o]mit, [a]bort? ")
            what='o'
            if what == "a":
                self.visual.print("Aborting.")
                exit(1)
            if what == "o":
                ids_to_insert = [i for i in ids_to_insert if i not in title_matches]

        if not ids_to_insert and False:
            self.visual.print("Nothing left to merge.")
            return
        other_collection.only_keep(ids_to_insert)
        # insert them
        self.visual.print("Proceeding to import {} entries:".format(len(ids_to_insert)))
        for i, ID in enumerate(ids_to_insert):
            entry = other_collection.entries[ID]
            strs = self.visual.gen_entry_enum_strings(entry, other_collection, i + 1, len(ids_to_insert))
            self.visual.print("Inserting {} {} {}".format(*strs))

            self.entry_collection.insert_new(entry)

        # self.visual.print("Updated collection:")
        # runner = Runner(self.conf, entry_collection = self.entry_collection)
        # runner.loop()

        self.visual.print_entry_enum(self.entry_collection.entries.values(), self.entry_collection)
        # write results
        self.write()

    def write(self, entry_col=None):
        if entry_col is None:
            entry_col = self.entry_collection
        with open("testfile.bib", "w") as f:
            bibtexparser.dump(entry_col.get_writable_db(), f)
