
import clipboard
from os.path import exists

import bibtexparser
from bibtexparser.bparser import BibTexParser


class Adder:
    bib_filepath = None

    def __init__(self, conf):
        """
        Adds copied bibtex entry to bibtex file
        """
        self.bib_filepath = conf.bib_path
        self.created_new = conf.created_new

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
