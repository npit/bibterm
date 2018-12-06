import os
from os.path import exists, basename, join
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser import customization
import re

class Reader:

    def __init__(self, conf=None):
        "docstring"
        self.conf = conf
        self.bib_path = conf.bib_path
        self.temp_dir = "/tmp/bib/"
        os.makedirs(self.temp_dir, exist_ok=True)

    def customizations(record):
        """Use some functions delivered by the library
        :param record: a record
        :returns: -- customized record
        """
        record = customization.type(record)
        record = customization.author(record)
        record = customization.editor(record)
        record = customization.journal(record)
        record = customization.keyword(record)

        # customization for 'keywords' (plural) field
        sep=',|;'
        if "keywords" in record:
            record["keywords"] = [i.strip() for i in re.split(sep, record["keywords"].replace('\n', ''))]

        title = record["title"]
        while title[0] == "{":
            title = title[1:]
        while title[-1] == "}":
            title = title[:-1]
        record["title"] = title

        # record = customization.link(record)
        record = customization.page_double_hyphen(record)
        # record = customization.doi(record)
        return record


    # preprocess a bib file to be readable
    def preprocess(self, bib_path):
        preprocessed_path = join(self.temp_dir, basename(bib_path))
        # preprocess
        applied_changes = False
        with open(bib_path) as f:
            newlines = []
            for line in f:
                if line.startswith("%"):
                    # skip it
                    if not applied_changes:
                        print("Deleting commented lines.")
                    applied_changes = True
                    continue
                newlines.append(line)
        if applied_changes:
            # write the modified file
            with open(preprocessed_path, "w") as f:
                f.writelines(newlines)
            print("Modified {} to {}:".format(self.bib_path, preprocessed_path))
        return preprocessed_path


    # Read bibtex file, preprocessing out comments
    def read(self):
        filename = self.preprocess(self.bib_path)
        # read it
        with open(filename) as f:
            parser = BibTexParser()
            parser.customization = Reader.customizations
            db = bibtexparser.load(f, parser=parser)
            print("Loaded {} entries from {}.".format(len(db.entries), self.bib_path))
        self.db = db
    
    def get_content(self):
        return self.db

