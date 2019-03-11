import os
import json
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

from writer import Writer


class EntryCollection:
    visual = None
    do_fix = None
    fixes = 0
    entries_fixed = 0
    modified_collection = False
    keyword_override_action = None

    def get_tag_information(self):
        return {"keep": list(self.keyword2id.keys()), "map": self.keywords_map}

    def __init__(self, bib_db, tags_info):
        self.bibtex_db = bib_db
        self.title2id = {}
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
            self.insert(ent)

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

    def remove(self, ID):
        # bibtex_db containers
        del self.bibtex_db.entries_dict[ID]
        idx = [i for i in range(len(self.bibtex_db.entries)) if self.bibtex_db.entries[i]["ID"] == ID]
        if len(idx) > 1:
            self.visual.error("Mutiple indexes with ID {} found to remove.".format(ID))
            exit(1)
        del self.bibtex_db.entries[idx[0]]
        # containers
        ID = ID.lower()
        title = self.entries[ID].title.lower()
        del self.entries[ID]
        self.id_list.remove(ID)
        self.title_list.remove(title)
        del self.title2id[title]
        self.modified_collection = True

    def replace(self, ent):
        # keep copies of id and title lists to preserve order
        id_idx = self.id_list.index(ent.ID.lower())
        title_idx = self.title_list.index(ent.title.lower())
        # remove existing
        self.remove(ent.ID)
        # insert it
        self.create(ent)
        # remove from back
        self.id_list.pop()
        self.title_list.pop()

        # restore to list position
        self.id_list.insert(id_idx, ent.ID.lower())
        self.title_list.insert(title_idx, ent.title.lower())
        self.modified_collection = True

    def correct_id(self, current_id, expected_id):
        # id
        self.visual.log("Correcting {}/{} (#{} fixed, {} fixes) id {} -> {}.".format(self.entry_index + 1, len(self.bibtex_db.entries), self.entries_fixed + 1, self.fixes, current_id, expected_id))
        # entries dict
        if expected_id in self.bibtex_db.entries_dict:
            self.visual.log("Correcting {} to {exp}, but {exp} already exists in underlying bibtex db.".format(current_id, exp=expected_id))
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

    def handle_keywords(self, ent, index_id):
        applied_changes = False
        if ent.keywords is None:
            return ent, False
        keywords = []
        keywords_final = []
        for raw_kw in ent.keywords:
            kw = raw_kw.lower()
            # replace spaces with dashes
            kw = re.sub("[ ]+", "-", kw)
            kw = re.sub('[^a-zA-Z-]+', '', kw)
            if not kw:
                continue
            if kw != raw_kw:
                self.fixes += 1
                self.visual.log("Correcting {}/{} (#{} fixed, {} fixes) [keyword] [{}] -> [{}].".format(self.entry_index + 1, len(self.bibtex_db.entries), self.entries_fixed + 1, self.fixes, raw_kw, kw))
                applied_changes = True
            # filter out rejected ones
            if kw in self.keywords_discard:
                continue
            # map the out mapped ones
            if kw in self.keywords_map:
                for value in self.keywords_map[kw]:
                    self.add_keyword_instance(value, index_id)
                    keywords_final.append(value)
                continue
            # and the encountered approved ones
            if kw in self.keyword2id:
                self.add_keyword_instance(kw, index_id)
                keywords_final.append(kw)
                continue
            keywords.append(kw)

        while keywords:
            self.visual.print_enum(keywords)
            if self.keyword_override_action is None:
                what = self.visual.ask_user("Process keywords for entry [{}] ".format(index_id),
                                         "Keep-all Discard-all *keep discard change #1 #2 #... #|  #*all ", check=False)
                cmd, *idx_args = what.strip().split()
                idx_list = [i - 1 for i in utils.get_index_list(idx_args, len(keywords))]
                if not idx_list:
                    idx_list = range(len(keywords))
                elif utils.matches(cmd, 'all'):
                    idx_list = range(len(keywords))
            else:
                self.visual.log("Applying action to all entries & keywords: {}".format(self.keyword_override_action))
                cmd, idx_list = self.keyword_override_action, range(len(keywords))

            if utils.matches(cmd, "keep"):
                applied_changes = True
                for i in idx_list:
                    self.add_keyword_instance(keywords[i], index_id)
                    keywords_final.append(keywords[i])
            elif utils.matches(cmd, "change"):
                applied_changes = True
                new_kws = self.visual.ask_user("Change keywords: {} to what?".format([keywords[i] for i in idx_list]))
                new_kws = new_kws.strip().split()
                for i in idx_list:
                    self.change_keyword(keywords[i], new_kws, index_id)
                keywords_final.extend(new_kws)
            elif utils.matches(cmd, "discard"):
                applied_changes = True
            elif utils.matches(cmd, "Keep-all"):
                # apply the action
                self.keyword_override_action = "keep"
                continue
            elif utils.matches(cmd, "Discard-all"):
                # apply the action
                self.keyword_override_action = "discard"
                continue
            else:
                self.visual.error("Invalid input.")
                continue
            # remove used up indexes
            keywords = [keywords[i] for i in range(len(keywords)) if i not in idx_list]

        # assign to the entry object
        ent.keywords = list(set(keywords_final))
        if applied_changes:
            self.fixes += 1
        return ent, applied_changes

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
                if self.need_fix(ID, "expected id: {}".format(expected_id)):
                    # correct the citation id
                    self.fixes += 1
                    self.correct_id(ID, expected_id)
                    ent.ID = expected_id
                    ID = expected_id
                    fixed_entry = True
        ent, applied_changes = self.handle_keywords(ent, ID)
        if applied_changes:
            fixed_entry = True
            kw_str = ",".join(ent.keywords)
            self.bibtex_db.entries_dict[ID]["keywords"] = kw_str
            for i in range(len(self.entries)):
                if self.bibtex_db.entries[i]["ID"] == ID:
                    self.bibtex_db.entries[i]["keywords"] = kw_str
        # fix title
        if title != title.strip() or title.strip()[-1] == ".":
            if self.need_fix(ID, "title artifacts: '{}'".format(title)):
                # make the correct title
                title = title.strip()
                if title[-1] == ".":
                    title = title[:-1]
                self.fixes += 1
                self.visual.log("Correcting {}/{} (#{} fixed, {} fixes) [title] [{}] -> [{}].".format(self.entry_index + 1, len(self.bibtex_db.entries), self.entries_fixed + 1, self.fixes, ent.title, title))
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
            what = self.visual.ask_user("Fix entry problem: [{} : {}]?".format(entry_id, problem), "yes no *Yes-all No-all")
            if utils.matches(what, "Yes-all"):
                self.do_fix = True
            if utils.matches(what, "No-all"):
                self.do_fix = False
            fix = self.do_fix if self.do_fix is not None else utils.matches(what, "yes")
        else:
            return self.do_fix
        return fix

    def create(self, ent, position=None):
        inserted = self.insert(ent, can_fix=False)
        if not inserted:
            return False
        if position is None:
            self.bibtex_db.entries.append(ent.raw_dict)
        else:
            self.bibtex_db.entries.insert(ent.raw_dict, position)
        # the following updates the entries dict
        self.bibtex_db.get_entry_dict()
        # make sure it's there
        if ent.ID not in self.bibtex_db.entries_dict:
            # self.visual.warn("Non existing ID on bibtex dict: {}, adding.".format(ent.ID))
            self.bibtex_db.entries_dict[ent.ID] = ent.raw_dict
        self.modified_collection = True
        return True

    def insert(self, ent, can_fix=True):
        if can_fix:
            ent = self.fix_entry(ent)
        ID = ent.ID.lower()
        title = ent.title.lower()
        # update object lookup dict
        if ID in self.entries:
            self.visual.error("Entry with id {} already in entries dict!".format(ID))
            return False
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
        return True

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
        value = joiner.join(value).strip()
        if value.endswith(","):
            value = value[:-1]
        return value.strip()

    def reset_modified(self):
        self.modified_collection = False

    # overwrite collection to the file specified by the configuration
    def overwrite_file(self, conf):
        writer = Writer(conf)
        writer.write(self)


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

    def has_file(self):
        return self.file is not None

    def has_keywords(self):
        return self.keywords is not None

    def has_keyword(self, kw):
        if not self.has_keywords():
            return False
        return kw in self.keywords

    def get_citation(self):
        return "\\cite{" + self.ID + "}"

    def set_file(self, file_path):
        self.raw_dict["file"] = file_path
        self.file = file_path
        self.modified_collection = True

    def set_keywords(self, kw):
        self.raw_dict["keywords"] = kw
        self.keywords = kw
        self.modified_collection = True

    def get_pretty_dict(self, compact=True):
        d = OrderedDict()
        for key in ["ENTRYTYPE", "ID", "author", "title", "year", "keywords", "file"]:
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


class Reader:

    def __init__(self, conf=None):
        "docstring"

        self.conf = conf
        self.visual = setup(conf)
        Entry.visual = self.visual
        EntryCollection.visual = self.visual
        self.bib_path = conf.bib_path
        self.tags_path = os.path.splitext(self.bib_path)[0] + ".tags.json"
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
        with open(self.tags_path) as f:
            self.tags_info = json.load(f)
        return EntryCollection(db, self.tags_info)

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

        if self.entry_collection.entries_fixed > 0:
            self.visual.message("Applied a total of {} fixes to {} entries.".format(self.entry_collection.fixes, self.entry_collection.entries_fixed))
            if self.visual.yes_no("Write fixes to the original source file: {}?".format(self.bib_path), default_yes=False):
                self.entry_collection.overwrite_file(self.conf)

    def get_entry_collection(self):
        return self.entry_collection

    def get_content(self):
        return self.db
