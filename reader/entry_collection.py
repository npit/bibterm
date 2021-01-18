import collections
import json
import os
import re
import time
from collections import OrderedDict
from os.path import basename, exists, join

import bibtexparser
from bibtexparser import customization
from bibtexparser.bparser import BibTexParser

import utils
from visual.instantiator import setup
from writer import Writer
from reader.entry import Entry

class EntryCollection:
    visual = None
    modified_collection = False
    keyword_override_action = None
    all_pdf_paths = []

    def get_tag_information(self):
        return {"keep": list(self.keyword2id.keys()), "map": self.keywords_map}

    def __init__(self, bib_db, tags_info):
        """Entry collection costructor"""
        self.bibtex_db = bib_db
        self.title2id = {}
        self.author2id = {}
        self.entries = {}
        self.maxlen_id = 0
        self.maxlen_title = 0
        self.id_list = []
        self.title_list = []
        self.keywords_discard = set()
        self.keywords_map = tags_info["map"]
        self.keyword2id = {kw: [] for kw in tags_info["keep"]}

        for valuelist in self.keywords_map.values():
            for value in valuelist:
                self.keyword2id[value] = []

        # check for duplicate ids
        all_ids = [x["ID"] for x in bib_db.entries]
        duplicates = [item for item, count in collections.Counter(all_ids).items() if count > 1]
        if duplicates:
            self.visual.error("{} duplicates found in the collection - fix them.\n{}".format(len(duplicates), "\n".join(duplicates)))
            exit(1)

        for i in range(len(bib_db.entries)):
            self.entry_index = i
            entry = bib_db.entries[i]
            ent = Entry(entry)
            ent = self.add_entry_to_collection_containers(ent)


    def get_searchable_format(self):
        return self.bibtex_db.entries_dict

    # check and log missing entry elements
    def check_for_missing_fields(self):
        missing_per_entry = {}
        missing_per_field = {"pages": [], "publisher": []}
        for e in self.entries.values():
            fields = []
            if not e.has_pages():
                # self.visual.error("Entry {} has no pages information".format(e.ID))
                fields.append("pages")
                missing_per_field["pages"].append(e.ID)
            if not e.has_publisher():
                # self.visual.error("Entry {} has no publisher information".format(e.ID))
                fields.append("publisher")
                missing_per_field["publisher"].append(e.ID)
            if fields:
                missing_per_entry[e.ID] = fields
        return missing_per_entry, missing_per_field

    def pdf_path_exists(self, path):
        return path in self.all_pdf_paths
    # check if num in [1, num_entries]
    def num_in_range(self, num):
        return (num >= 1 and num <= len(self.entries))

    def maxlens(self, id_list=None):
        if id_list is None:
            return len(self.entries), self.maxlen_id, self.maxlen_title
        return len(id_list), max(list(map(len, id_list))), max([len(self.entries[ID].title) for ID in id_list])

    def only_keep(self, keep_ids):
        for ID in self.id_list:
            if ID in keep_ids:
                continue
            title = self.entries[ID].title.lower()
            self.id_list.remove(ID)
            del self.entries[ID]
            self.title_list.remove(title)
            del self.title2id[title]

    def remove(self, ID, do_modify=True):
        # bibtex_db containers
        del self.bibtex_db.entries_dict[ID]
        idx = [i for i in range(len(self.bibtex_db.entries)) if self.bibtex_db.entries[i]["ID"] == ID]
        if len(idx) != 1:
            self.visual.error("Mutiple/no indexes with ID {} found to remove: {}.".format(ID, idx))
            exit(1)
        del self.bibtex_db.entries[idx[0]]
        self.visual.log(f"Removed ID: {ID}, index: {idx[0]}")
        # containers
        ID = ID.lower()
        title = self.entries[ID].title.lower()
        del self.entries[ID]
        self.id_list.remove(ID)
        self.title_list.remove(title)
        del self.title2id[title]
        if do_modify:
            self.modified_collection = True

    def replace(self, ent, old_id=None):
        if old_id is None:
            old_id = ent.ID
        # keep copies of id and title lists to preserve order
        id_idx = self.id_list.index(old_id.lower())
        title_idx = self.title_list.index(ent.title.lower())
        # remove existing
        self.remove(old_id)
        # insert it
        self.add_entry(ent, can_replace=False)
        # remove from back
        self.id_list.pop()
        self.title_list.pop()

        # restore to list position
        self.id_list.insert(id_idx, ent.ID.lower())
        self.title_list.insert(title_idx, ent.title.lower())
        self.modified_collection = True

    def has_entry(self, entry_id):
        return entry_id in self.id_list

    def add_keyword_instance(self, kw, entry_id):
        if kw not in self.keyword2id:
            self.keyword2id[kw] = []
        self.keyword2id[kw].append(entry_id)

    def change_keyword(self, kw, new_kws, entry_id):
        if kw in self.keywords_map and self.keywords_map[kw] != new_kws:
            self.visual.log("Specified different mapping: {} to existing one: {}, for encountered keyword: {}".format(kw, self.keywords_map[kw], new_kws))

        self.keywords_map[kw] = new_kws
        for nkw in new_kws:
            self.add_keyword_instance(nkw, entry_id)


    def add_entry(self, ent, can_replace=True):
        """Add input entry to the collection"""
        if self.has_entry(ent.ID):
            if not can_replace:
                self.visual.error(f"Entry {ent.ID} already exists in the collection!")
                return None
            # delete existing, to replace
            self.remove(ent)
        ent = self.add_entry_to_collection_containers(ent)
        if ent is None:
            return ent
        self.add_entry_to_bibtex_db(ent)
        self.visual.log(f"Added ID: {ent.ID}")
        return ent

    def add_new_entry(self, ent):
        """Add a new entry to the collection"""
        ent.inserted = time.strftime("%D")
        ent = self.add_entry(ent)
        if ent is not None:
          self.modified_collection = True
        return ent

    def add_entry_to_bibtex_db(self, ent):
        """Create a new, non-existing entry"""

        # add additional fields manually to the dict
        ent.consolidate_dict()
        self.bibtex_db.entries.append(ent.raw_dict)
        # the following updates the entries dict
        # self.bibtex_db.get_entry_dict()
        # # make sure it's there
        # if ent.ID not in self.bibtex_db.entries_dict:
        #     self.bibtex_db.entries_dict[ent.ID] = ent.raw_dict

    def get_entry(self, lookup_id):
        return self.entries[lookup_id.lower()]

    def add_entry_to_collection_containers(self, ent):
        """Update utility containers (dicts, lists, etc.) of the entry collection class"""

        ID = ent.ID.lower()
        title = ent.title.lower()
        # update object lookup dict
        if ID in self.entries:
            self.visual.error("Entry with id {} already in entries dict!".format(ID))
            return None
        self.entries[ID] = ent
        # update title-id mapping
        self.title2id[title] = ID
        for auth in ent.author:
            if auth not in self.author2id:
                self.author2id[auth] = []
            self.author2id[auth].append(ID)

        # update ids and titles lists
        self.id_list.append(ID)
        self.title_list.append(title)
        # update maximum ID / title lengths
        if len(ent.ID) > self.maxlen_id:
            self.maxlen_id = len(ent.ID)
        if len(ent.title) > self.maxlen_title:
            self.maxlen_title = len(ent.title)
        if ent.file:
            self.all_pdf_paths.append(ent.file)
        return ent

    def find_ID_(self, thelist, ID):
        for i in range(len(self.entries)):
            if self.entries[i].ID == ID:
                return i

    def get_writable_db(self):
        for i, entry_dict in enumerate(self.bibtex_db.entries):
            entry_id = entry_dict["ID"]
            entry = self.entries[entry_id.lower()]
            self.bibtex_db.entries[i] = entry.get_writable_dict()
        self.bibtex_db._make_entries_dict()
        return self.bibtex_db

        # stringify_keys = ["author", "keywords", "journal", "link"]
        # for key in stringify_keys:
        #     for i in range(len(self.bibtex_db.entries)):
        #         if key not in self.bibtex_db.entries[i]:
        #             continue
        #         if type(self.bibtex_db.entries[i][key]) != str:
        #             self.bibtex_db.entries[i][key] = self.stringify(self.bibtex_db.entries[i][key], key)
        #     for ID in self.bibtex_db.entries_dict:
        #         if key not in self.bibtex_db.entries_dict[ID]:
        #             continue
        #         if type(self.bibtex_db.entries_dict[ID][key]) != str:
        #             self.bibtex_db.entries_dict[ID][key] = self.stringify(self.bibtex_db.entries_dict[ID][key], key)
        # return self.bibtex_db

    def reset_modified(self):
        self.modified_collection = False

    def set_modified(self):
        self.modified_collection = True

    # overwrite collection to the file specified by the configuration
    def overwrite_file(self, conf):
        writer = Writer(conf)
        writer.write(self)