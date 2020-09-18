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
from reader.rules import *
from reader.entry_collection import EntryCollection
from reader.entry import Entry

class Reader:

    def __init__(self, conf=None):
        """Constructor"""

        self.conf = conf
        self.visual = setup(conf)
        Entry.visual = self.visual
        EntryCollection.visual = self.visual
        self.should_apply_fix_to_all = None
        self.num_fixes = 0

        try:
            self.bib_path = conf.get_user_settings()["bib_path"]
        except KeyError:
            self.visual.fatal_error("No bib_path set in user_settings!")
        self.tags_path = os.path.splitext(self.bib_path)[0] + ".tags.json"
        self.temp_dir = self.conf.get_tmp_dir()
        os.makedirs(self.temp_dir, exist_ok=True)

        self.setup_entry_fix_rules()

    def setup_entry_fix_rules(self):
        """Define entry fixing rules"""
        self.rules = [BasicFix(), KeywordFix(), TitleFix(), IDFix()]
        self.active_rules = self.rules

    def customizations(record):
        """Modify bibtex database object entries
        :param record: a record
        :returns: -- customized record
        """
        # record = customization.type(record)
        record = customization.author(record)
        # record = customization.editor(record)
        # record = customization.journal(record)
        # record = customization.keyword(record)

        # customization for 'keywords' (plural) field
        sep = ',|;'
        if "keywords" in record:
            record["keywords"] = [i.strip() for i in re.split(sep, record["keywords"].replace('\n', ''))]

        title = record["title"]
        while title[0] == "{":
            title = title[1:]
        while title[-1] == "}":
            title = title[:-1]
        record["title"] = title

        # record = customization.link(record)
        # record = customization.page_double_hyphen(record)
        # record = customization.doi(record)
        return record

    # preprocess a bib file to be readable
    def preprocess(self, bib_path):
        # preprocess
        applied_changes = False
        with open(bib_path) as f:
            newlines = []
            for line in f:
                if line.startswith("%"):
                    # skip it
                    if not applied_changes:
                        self.visual.log("Deleting commented lines.")
                    applied_changes = True
                    continue
                newlines.append(line)
        if applied_changes:
            preprocessed_path = join(self.temp_dir, basename(bib_path))
            # write the modified file
            with open(preprocessed_path, "w") as f:
                f.writelines(newlines)
            self.visual.print("Modified {} to {}:".format(self.bib_path, preprocessed_path))
            return preprocessed_path
        return bib_path

    def load_collection(self, db):
        if os.path.exists(self.tags_path):
            with open(self.tags_path) as f:
                self.tags_info = json.load(f)
        else:
            self.tags_info = {"keep":[],"map":{}}
        db = EntryCollection(db, self.tags_info)
        self.apply_fix_rules(db)
        return db

    def apply_fix_rules(self, db):
        """ Apply rules to fix entry contents """
        for rule in self.active_rules:
            self.visual.log(f"Applying fix rule: {rule.name}")
            self.should_apply_fix_to_all = None
            if rule.must_inform_db:
                rule.configure_db(db)
            # preload enumeration since a rule may change IDs
            idxs_ids = list(enumerate(db.entries))
            for entry_idx, entry_id in idxs_ids:
                entry = db.entries[entry_id]
                rule.make_fix(entry)
                if rule.is_applicable():
                    if rule.needs_confirmation:
                        self.confirm_and_apply_fix_rule(entry, rule, db)
                    else:
                        rule.apply(entry)
                    if rule.was_applied():
                        self.num_fixes += 1
                        self.visual.log(f"Correcting {entry_idx+1}/{len(db.entries)} {entry_id} (# {self.num_fixes} fixes) {rule.get_log()}")
                        db.set_modified()
                    # if (not rule.needs_confirmation) or self.confirm_fix(entry, rule.get_message()):
                    #     rule.apply(entry)
                    #     self.visual.log(f"Correcting {entry_idx+1}/{len(db.entries)} {entry_id} (# {self.num_fixes} fixes) {rule.get_log()}")

    def confirm_and_apply_fix_rule(self, entry, rule, collection):
        """Ask user confirmation for applying a fix"""
        if self.should_apply_fix_to_all is not None:
            if self.should_apply_fix_to_all:
                rule.apply(entry)
            return
        while True:
            self.visual.print_entry_contents(entry)
            what = self.visual.ask_user(rule.get_confirmation_message(entry), "edit-manually quit " + rule.get_user_confirmation_options())
            # manual fix with a text editor
            if utils.matches(what, "edit-manually"):
                collection.remove(entry.ID)
                updated_entry = Entry.from_string(self.edit_entry_manually(entry))
                modified = updated_entry.raw_dict != entry.raw_dict
                collection.add_new_entry(entry)
                self.visual.message("Fixed entry manually:")
                self.visual.print_entry_contents(entry)
                if modified:
                    collection.set_modified()
                return
            if utils.matches(what, "quit"):
                self.visual.message("Bye!")
                exit(1)

            # parse via the rule
            try:
                rule.parse_confirmation_response(what, entry)
            except ValueError as ve:
                self.visual.error(str(ve))
                break
            self.should_apply_fix_to_all = rule.decision_for_all_entries
            if rule.is_finished():
                break

        return entry

    # Read a collection of entries
    def read_entry_list(self, elist):
        if type(elist[0]) in (dict, OrderedDict):
            entries = {}
            for el in elist:
                ent = Entry.from_dict(el)
                entries[ent.ID] = ent
            return entries
        elif type(elist[0]) is str:
            self.read_string("\n".join(elist))
            return self.entry_collection.entries

    # Read from string
    def read_string(self, string):
        if len(string) == 0 or string is None:
            return
        parser = BibTexParser()
        parser.customization = Reader.customizations
        db = bibtexparser.loads(string, parser=parser)
        self.visual.log("Loaded {} entries from supplied string.".format(len(db.entries)))
        self.entry_collection = self.load_collection(db)

    # Read bibtex file, preprocessing out comments
    def read(self, input_file=None):
        if input_file is None:
            input_file = self.preprocess(self.bib_path)
        self.visual.log("Reading from file {}.".format(input_file))
        if not exists(input_file):
            self.visual.error("File {} does not exist.".format(input_file))
            exit(1)
        # read it
        with open(input_file) as f:
            parser = BibTexParser()
            parser.customization = Reader.customizations
            db = bibtexparser.load(f, parser=parser)
            self.visual.log("Loaded {} entries from file {}.".format(len(db.entries), self.bib_path))
        self.db = db
        self.entry_collection = self.load_collection(db)

        updated_tags = self.entry_collection.get_tag_information()
        if updated_tags != self.tags_info:
            self.tags_info = updated_tags
            if self.visual.yes_no("Write updated tags to the original file: {}?".format(self.tags_path), default_yes=False):
                with open(self.tags_path, "w") as f:
                    f.write(json.dumps(updated_tags, indent=4, sort_keys=True))

        if self.num_fixes > 0:
            self.visual.message("Applied a total of {} fixes.".format(self.num_fixes))
            if self.visual.yes_no("Write fixes to the original source file: {}?".format(self.bib_path), default_yes=False):
                self.entry_collection.overwrite_file(self.conf)
                self.entry_collection.reset_modified()

    def get_entry_collection(self):
        return self.entry_collection

    def get_content(self):
        return self.db
