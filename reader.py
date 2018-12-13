import os
import utils
from collections import OrderedDict
from stopwords import stopwords
from os.path import exists, basename, join
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser import customization
import re
from visual import setup
import collections

from writer import BibWriter


class EntryCollection:
    visual = None
    do_fix = None
    fixes = 0
    entries_fixed = 0

    def __init__(self, bib_db):
        self.bibtex_db = bib_db
        self.title2id = {}
        self.entries = {}
        self.maxlen_id = 0
        self.maxlen_title = 0
        self.id_list = []
        self.title_list = []

        # check for duplicate ids
        all_ids = [x["ID"] for x in bib_db.entries]
        duplicates = [item for item, count in collections.Counter(all_ids).items() if count > 1]
        if duplicates:
            self.visual.print("{} duplicates found:\n{}\n".format(len(duplicates), "\n".join(duplicates)))
            self.visual.print("Fix them first, bye!")
            exit(1)

        for i in range(len(bib_db.entries)):
            self.entry_index = i
            # print("All ids:", ",".join())
            entry = bib_db.entries[i]
            # print("Got entry to insert: ", entry["ID"], " bib etnries", len(bib_db.entries))
            # print("bib dict entries:", len(bib_db.entries_dict))
            # print("entries:", len(self.entries))
            # print("id list:", len(self.id_list))
            # print("title list:", len(self.title_list))
            ent = Entry(entry)
            self.insert(ent)

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

    def remove(self, ID):
        # bibtex_db containers
        del self.bibtex_db.entries_dict[ID]
        idx = [i for i in range(len(self.bibtex_db.entries)) if self.bibtex_db.entries[i]["ID"] == ID]
        if len(idx) > 1:
            self.visual.print("Mutiple indexes with ID {} found to remove.".format(ID))
            exit(1)
        del self.bibtex_db.entries[idx[0]]
        # containers
        ID = ID.lower()
        title = self.entries[ID].title.lower()
        del self.entries[ID]
        self.id_list.remove(ID)
        self.title_list.remove(title)
        del self.title2id[title]

    def replace(self, ent):
        # remove existing
        self.remove(ent.ID)
        # insert it
        self.insert(ent, can_fix=False)

    def correct_id(self, current_id, expected_id):
        # id
        self.visual.print("Correcting {}/{} (#{} fixed, {} fixes) id {} -> {}.".format(self.entry_index + 1, len(self.bibtex_db.entries), self.entries_fixed + 1, self.fixes, current_id, expected_id))
        # entries dict
        if expected_id in self.bibtex_db.entries_dict:
            self.visual.print("Correcting {} to {exp}, but {exp} already exists in underlying bibtex db.".format(current_id, exp=expected_id))
            exit(1)
        # assign the new dict key
        self.bibtex_db.entries_dict[expected_id] = self.bibtex_db.entries_dict[current_id]
        # delete existing key
        del self.bibtex_db.entries_dict[current_id]

        # entries list
        for i in range(len(self.bibtex_db.entries)):
            if self.bibtex_db.entries[i]["ID"] == current_id:
                self.bibtex_db.entries[i]["ID"] = expected_id
                break

    def fix_entry(self, ent):
        fixed_entry = False
        ID = ent.ID
        title = ent.title
        year = ent.year
        authorname = ent.author
        missing_fields = []

        if authorname is None:
            missing_fields.append("author")
        if ent.year is None:
            missing_fields.append("year")
        if missing_fields:
            self.visual.print("Missing fields: {}".format(missing_fields))
            self.visual.print_entry_contents(ent)
        else:
            authorname = authorname[0].lower()
            if "," in authorname:
                authorname = authorname.split(",")[0]
            if "-" in authorname:
                authorname = authorname.split("-")[0]
            authorname = re.sub('[^a-zA-Z]+', '', authorname)
            # remove stopwords, get first word
            title_first = [x for x in title.strip().lower().split() if x not in stopwords]
            title_first = title_first[0]
            for x in ["-", "/"]:
                if x in title:
                    # for dashes or slashes, keep the first part
                    title_first = title_first.split(x)[0]
            title_first = re.sub('[^a-zA-Z]+', '', title_first)
            expected_id = "{}{}{}".format(authorname, year, title_first)
            if ID != expected_id:
                if self.need_fix(ID, "id mismatch: {}".format(expected_id)):
                    # correct the citation id
                    self.fixes += 1
                    self.correct_id(ID, expected_id)
                    ent.ID = expected_id
                    ID = expected_id
                    fixed_entry = True

        # fix title
        if title != title.strip() or title.strip()[-1] == ".":
            if self.need_fix(ID, "title artifacts"):
                # make the correct title
                title = title.strip()
                if title[-1] == ".":
                    title = title[:-1]
                self.fixes += 1
                self.visual.print("Correcting {}/{} (#{} fixed, {} fixes) [title] [{}] -> [{}].".format(self.entry_index + 1, len(self.bibtex_db.entries), self.entries_fixed + 1, self.fixes, ent.title, title))
                # set it to the bibtex dict
                self.bibtex_db.entries_dict[ID]["title"] = title
                # set it to the bibtex list
                for i in range(len(self.entries)):
                    if self.bibtex_db.entries[i]["ID"] == ID:
                        self.bibtex_db.entries[i]["title"] = title
                ent.title = title
                fixed_entry = True
        if fixed_entry:
            self.entries_fixed += 1
        else:
            # self.visual.print("Did not correct entry {}/{} id: {}.".format(self.entry_index + 1, len(self.bibtex_db.entries), ent.ID))
            pass
        return ent

    def need_fix(self, entry_id, problem):
        fix = False
        if self.do_fix is None:
            what = self.visual.input("Fix entry problem: [{} : {}]?".format(entry_id, problem), "yes no *Yes-all No-all")
            if utils.matches(what, "Yes-all"):
                self.do_fix = True
            if utils.matches(what, "No-all"):
                self.do_fix = False
            fix = self.do_fix if self.do_fix is not None else utils.matches(what, "yes")
        else:
            return self.do_fix
        return fix

    def create(self, ent):
        self.insert(ent, can_fix=False)
        self.bibtex_db.entries.append(ent.raw_dict)
        # the following updates the entries dict
        self.bibtex_db.get_entry_dict()
        # make sure it's there
        if ent.ID not in self.bibtex_db.entries_dict:
            self.visual.warn("Non existing ID on bibtex dict: {}, adding.".format(ent.ID))
            self.bibtex_db.entries_dict[ent.ID] = ent.raw_dict

    def insert(self, ent, can_fix=True):
        if can_fix:
            ent = self.fix_entry(ent)
        ID = ent.ID.lower()
        title = ent.title.lower()
        # update object lookup dict
        if ID in self.entries:
            self.visual.print("Entry with id {} already in entries dict!".format(ID))
            exit(1)
        self.entries[ID] = ent
        # update title-id mapping
        self.title2id[title] = ID
        # update ids and titles lists
        self.id_list.append(ID)
        self.title_list.append(title)
        # update maximum ID / title lengths
        if len(ent.ID) > self.maxlen_id:
            self.maxlen_id = len(ent.ID)
        if len(ent.title) > self.maxlen_title:
            self.maxlen_title = len(ent.title)

    def find_ID_(self, thelist, ID):
        for i in range(len(self.entries)):
            if self.entries[i].ID == ID:
                return i

    def get_writable_db(self):
        stringify_keys = ["author", "keywords", "journal", "link"]
        for key in stringify_keys:
            for i in range(len(self.bibtex_db.entries)):
                if key not in self.bibtex_db.entries[i]:
                    continue
                if type(self.bibtex_db.entries[i][key]) != str:
                    self.bibtex_db.entries[i][key] = self.stringify(self.bibtex_db.entries[i][key], key)
            for ID in self.bibtex_db.entries_dict:
                if key not in self.bibtex_db.entries_dict[ID]:
                    continue
                if type(self.bibtex_db.entries_dict[ID][key]) != str:
                    self.bibtex_db.entries_dict[ID][key] = self.stringify(self.bibtex_db.entries_dict[ID][key], key)
        return self.bibtex_db

    def stringify(self, value, key):
        joiner = " and " if key == "author" else ", "
        value = joiner.join(value)
        return re.sub("[{}]", "", value)


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

    def __init__(self, kv):
        for key in kv:
            self.__setattr__(key, kv[key])
        self.raw_dict = kv

    def has_keywords(self):
        return self.keywords is not None

    def has_keyword(self, kw):
        if not self.has_keywords():
            return False
        return kw in self.keywords

    def get_citation(self):
        return "\\cite{" + self.ID + "}"

    def get_pretty_dict(self):
        d = OrderedDict()
        for key in ["ENTRYTYPE", "ID", "author", "title", "year"]:
            if key in self.raw_dict:
                d[key] = self.raw_dict[key]
        return d


class Reader:

    def __init__(self, conf=None):
        "docstring"

        self.conf = conf
        self.visual = setup(conf)
        Entry.visual = self.visual
        EntryCollection.visual = self.visual
        self.bib_path = conf.bib_path
        self.temp_dir = "/tmp/bib/"
        os.makedirs(self.temp_dir, exist_ok=True)

    def customizations(record):
        """Use some functions delivered by the library
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
                        self.visual.print("Deleting commented lines.")
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

    # Read from string
    def read_string(self, string):
        parser = BibTexParser()
        parser.customization = Reader.customizations
        db = bibtexparser.loads(string, parser=parser)
        self.visual.print("Loaded {} entries from string.".format(len(db.entries)))
        self.entry_collection = EntryCollection(db)

    # Read bibtex file, preprocessing out comments
    def read(self):
        filename = self.preprocess(self.bib_path)
        self.visual.print("Reading from file {}.".format(filename))
        if not exists(filename):
            self.visual.print("File {} does not exist.".format(filename))
            exit(1)
        # read it
        with open(filename) as f:
            parser = BibTexParser()
            parser.customization = Reader.customizations
            db = bibtexparser.load(f, parser=parser)
            self.visual.print("Loaded {} entries from {}.".format(len(db.entries), self.bib_path))
        self.db = db
        self.entry_collection = EntryCollection(db)

        if self.entry_collection.entries_fixed > 0:
            self.visual.print("Applied a total of {} fixes to {} entries.".format(self.entry_collection.fixes, self.entry_collection.entries_fixed))
            what = self.visual.input("Write fixes to the original source file: {}?".format(self.bib_path), "yes *no")
            if utils.matches(what, "no"):
                pass
            else:
                writer = BibWriter(self.conf, entry_collection=self.entry_collection)
                writer.write(self.entry_collection)

    def get_entry_collection(self):
        return self.entry_collection

    def get_content(self):
        return self.db
