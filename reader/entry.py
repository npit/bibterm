import collections
import json
import os
import re
import time
from collections import OrderedDict
from os.path import basename, exists, join

import bibtexparser
from bibtexparser import customization
from writer import dict_to_raw_bibtex

import utils
from visual.instantiator import setup

class Entry:
    ENTRYTYPE = None
    ID = None
    archiveprefix = None
    arxivid = None
    author = None
    booktitle = None
    doi = None
    eprint = None
    file = None
    isbn = None
    issn = None
    keywords = None
    link = None
    number = None
    pages = None
    pmid = None
    publisher = None
    title = None
    url = None
    volume = None
    year = None
    inserted = None

    useful_keys = ["ENTRYTYPE", "ID", "author", "title", "year", "keywords", "file", "tags", "inserted"]
    # keys to show a very short description of the entry
    shorthand_keys = ["ID", "author", "title"]
    # keys to identify new candidate entries
    discovery_keys = ["title", "year", "author"]
    # aliases
    alias_keys = {"a": "author", "t": "title", "y": "year"}
    key_types = {"author": str, "title": str, "ID": str, "year": int, "keywords": list, "file": str, "inserted": str}


    def satisfies_filter(self, func):
        return func(self)

    @staticmethod
    def from_string(s):
        return Entry.from_dict(json.loads(s))

    @staticmethod
    def from_dict(ddict):
        # apply fixes
        # year has to be a string
        if "year" in ddict and type(ddict["year"]) == int:
            ddict["year"] = str(ddict["year"])
        e = Entry(ddict)
        return e

    def get_value(self, key, postproc=False):
        try:
            value = self.raw_dict[key]
        except KeyError:
            value = ""
        if postproc:
            if type(value) is list:
                value = ",".join([str(x) for x in value])
        return value

    def set_dict_value(self, key, value):
        if key == "pages":
            self.pages = value
        elif key == "publisher":
            self.publisher = value
        else:
            pass
        self.raw_dict[key] = value

    def __init__(self, kv):
        for key in kv:
            self.__setattr__(key, kv[key])
        self.raw_dict = kv

    def consolidate_dict(self):
        """Add entry fields to the raw dictionary"""
        self.raw_dict["inserted"] = str(self.inserted) if self.inserted is not None else ""

    def get_raw_dict(self):
        return self.raw_dict


    def get_writable_dict(self):
        self.make_writable_dict()
        return self.writable_dict

    def make_writable_dict(self):
        stringify_keys = ["author", "keywords", "journal", "link"]
        self.writable_dict = {k: v for (k, v) in self.raw_dict.items()}
        for key in stringify_keys:
            joiner = " and " if key == "author" else ", "
            if key not in self.writable_dict:
                continue
            value = self.writable_dict[key]
            if type(value) != str:
                value = utils.stringify(value, key, joiner=joiner)
                self.writable_dict[key] = value


    def get_raw_bibtex_string(self):
        s = []
        for k, v in self.get_writable_dict().items():
            if k in ["ENTRYTYPE", "ID"]:
                continue
            content = "{" + str(k) + " = " + str(v) + "}"
            s.append(content)
        s = ",\n".join(s)
        s = "@" + self.raw_dict["ENTRYTYPE"] + "{" + self.raw_dict["ID"] + s + "}"
        return s

    def has_file(self):
        return self.file is not None

    def has_keywords(self):
        return self.keywords is not None

    def has_publisher(self):
        return self.publisher is not None

    def has_pages(self):
        return self.pages is not None

    def has_keyword(self, kw):
        if not self.has_keywords():
            return False
        return kw in self.keywords

    def get_citation(self):
        return "\\cite{" + self.ID + "}"

    def set_file(self, file_path):
        self.raw_dict["file"] = file_path
        self.file = file_path

    def set_keywords(self, kw):
        self.set_dict_value("keywords", kw)
        self.keywords = kw

    def get_discovery_view(self):
        """Return only information to identify the paper"""
        return list(self.get_pretty_dict(keys=Entry.discovery_keys).values())

    def get_pretty_dict(self, compact=True, keys=None):
        d = OrderedDict()
        if keys is None:
            keys = self.useful_keys
        for key in keys:
            if key in self.raw_dict:
                value = self.raw_dict[key]
                if compact:
                    # concat. list into a string to display in a single line
                    if type(value) == list:
                        value = " ".join(value).strip()
                    # skip empty values
                    if not value:
                        continue
                d[key] = value
        return d

    def has_canonic_filename(self, entry):
        return entry.file.spit(os.sep) == self.get_canonic_filename()

    def get_canonic_filename(self):
        return  self.ID + ".pdf"

    def __str__(self):
        keys = Entry.shorthand_keys
        x = self.get_pretty_dict(compact=True, keys=keys)
        keys = [k for k in keys if k in x.keys()]
        return ". ".join(["{}: {}".format(k, x[k]) for k in keys])

    def __repr__(self):
        return self.__str__()

    def set_title(self, title):
        self.title = title
        self.set_dict_value("title", title)

    def set_id(self, ID):
        self.ID = ID
        self.set_dict_value("ID", ID)

