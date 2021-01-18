import re
from reader.bibtex_key_generation import KeyGenerator
import utils

""" Listing of entry fixing rules
"""
class FixRule:
    """Abstract class for entry fix rule"""
    name = ""
    log = ""
    applicable = False
    # the objects prior and aftex applying the fix
    reference_object = None
    fixed_object = None
    last_fix_was_applied = None
    message = None
    log_message = None
    # whether the fix needs to be initialized with the collection
    must_inform_db = False
    # whether the rule needs manual confirmation
    needs_confirmation = True
    # whether a rule should be applied to all entries
    decision_for_all_entries = None
    def __init__(self):
        pass
    def configure_db(self, collection):
        pass
    def is_applicable(self):
        return self.reference_object != self.fixed_object
    def apply(self, entry):
        """Apply the fix"""
        self.last_fix_was_applied = True
    def make_fix(self, entry):
        """Build / prepare the fix"""
        self.log_message = None
        self.last_fix_was_applied = False
    def get_message(self):
        return self.message
    def get_log(self):
        if self.log_message is not None:
            return self.log_message
        return f"Applied {self.name} fix: {self.reference_object} -> {self.fixed_object}"
    def get_confirmation_message(self, entry):
        """Get prompt message prior to display prior to user confirmation"""
        return f"Fix entry problem: [{entry.ID} : {self.get_message()}]?"
    def get_user_confirmation_options(self):
        """Get available confirmation options"""
        # default user interaction is boolean confirmation
        return "yes no *Yes-all No-all"
    def parse_confirmation_response(self, response, entry):
        applied_for_this_entry = False
        if utils.matches(response, "Yes-all"):
            self.decision_for_all_entries = True
            applied_for_this_entry = True
        elif utils.matches(response, "No-all"):
            self.decision_for_all_entries = False
        if utils.matches(response, "yes"):
            self.apply(entry)
            applied_for_this_entry = True
        return applied_for_this_entry, self.decision_for_all_entries

    def is_finished(self):
        """Whether interaction is complete"""
        return True
    def was_applied(self):
        """Whether the latest candidate application took place"""
        return self.last_fix_was_applied

class BasicFix(FixRule):
    bad_fields = []
    name = "basic"
    def __init__(self):
        super().__init__()

    def make_fix(self, entry):
        super().make_fix(entry)
        self.bad_fields = []
        self.reference_object = entry
        if self.reference_object.author is None:
            # self.reference_object.author = ""
            self.bad_fields.append("author")
        if self.reference_object.year is None:
            # self.reference_object.year = ""
            self.bad_fields.append("year")
        if self.reference_object.title is None:
            self.bad_fields.append("title")
        self.message = f"Bad fields: {self.bad_fields}"

    def is_applicable(self):
        return len(self.bad_fields) > 0

    def apply(self, entry):
        super().apply(entry)
        pass
        # if "author" in self.bad_fields:
        #     self.reference_object.author = ""
        # if "year" in self.bad_fields:
        #     self.reference_object.year = ""
        # if "title" in self.bad_fields:
        #     self.reference_object.year = ""
        # self.log_message = f"Fixed bad field(s): {self.bad_fields}" 


    def get_user_confirmation_options(self):
        """Get basic info handling confirmation options"""
        # let the reader handling options deal with it
        return ""

    def get_confirmation_message(self, entry):
        """Get prompt message prior to display prior to user confirmation"""
        return f"\nBasic entry information missing: [{entry.ID} : fields: {self.bad_fields}]?"



class AuthorFix(FixRule):
    """Fix for author component of the entry ID"""
    name = "author"
    def __init__(self):
        super().__init__()

    def apply(self, entry):
        super().apply(entry)
        pass

class TitleFix(FixRule):
    """Fix for the title component of the entry ID"""
    name = "title"
    def __init__(self):
        super().__init__()

    def make_fix(self, entry):
        super().make_fix(entry)
        title = entry.title
        self.reference_object = title
        # remove surrounding whitespace and trailing dot
        title = title.strip()
        title = title[:-1] if title[-1] == "." else title
        self.fixed_object = title.strip()
        self.message = f"fixed title: {self.fixed_object}"
    def apply(self, entry):
        super().apply(entry)
        entry.set_title(self.fixed_object)

class IDFix(FixRule):
    """Fix for the entry ID"""
    name = "key"
    def __init__(self):
        super().__init__()
        self.key_generator = KeyGenerator()
        self.must_inform_db = True
    def configure_db(self, db):
        self.db = db
    def make_fix(self, entry):
        super().make_fix(entry)
        self.reference_object = entry.ID
        self.fixed_object= self.key_generator.generate_key(entry)
        self.message = f"expected id: {self.fixed_object}"
    def apply(self, entry):
        super().apply(entry)
        # remove the old entry from the db
        self.db.remove(self.reference_object)
        # update the ID
        entry.set_id(self.fixed_object)
        # add it
        self.db.add_entry(entry, can_replace=False)

class KeywordFix(FixRule):
    """Fix for the entry keywords"""
    name = "keyword"
    undefined_keywords_message = ""
    undefined_keywords = []
    approved_keywords = []
    resolved_keywords = []
    # cached user command
    user_command_cache = None
    def __init__(self):
        super().__init__()
        self.must_inform_db = True

    def configure_db(self, db):
        """Get keyword discarding / mapping from the collection"""
        self.discarded_keywords = db.keywords_discard
        self.mapped_keywords = db.keywords_map
        self.existing_keywords = db.keyword2id
        self.db = db

    def apply_to_db(self, entry):
        for kw in self.approved_keywords:
            self.db.add_keyword_instance(kw, entry.ID)

    def format_keyword(self, kw):
        """Process a single keyword element"""
        kw = kw.lower()
        # replace spaces with dashes
        kw = re.sub("[ ]+", "-", kw)
        kw = re.sub('[^a-zA-Z-]+', '', kw)
        return kw


    def is_applicable(self):
        return len(self.undefined_keywords) > 0 # or (self.reference_object != self.approved_keywords)

    def apply(self, entry):
        """Assign the keywords to the entry and update the db's keyword trackers"""
        super().apply(entry)
        entry.set_keywords(self.approved_keywords)
        entry.set_keywords(self.resolved_keywords)
        self.apply_to_db(entry)
        self.fixed_object = self.resolved_keywords

    def make_fix(self, entry):
        super().make_fix(entry)
        if entry.keywords is None:
            return
        self.reference_object = entry.keywords
        keywords = self.process_keywords(entry.keywords)

        # consume defined keywords
        self.approved_keywords = [k for k in keywords if k in self.existing_keywords]
        self.undefined_keywords = [k for k in keywords if k not in self.approved_keywords]

        if not self.undefined_keywords:
            return
        self.undefined_keywords_message = "\n".join(utils.make_indexed_list(self.undefined_keywords))
        self.reference_object = self.undefined_keywords
        self.log_message = ""

        return

    def get_user_confirmation_options(self):
        """Get keyword handling confirmation options"""
        # default user interaction is boolean confirmation
        # return "*keep discard change #<indexes> #| #*all"
        return "*keep discard Keep-all Discard-All #<indexes> #| #*all"

    def get_confirmation_message(self, entry):
        """Get prompt message prior to display prior to user confirmation"""
        return self.undefined_keywords_message + f"\nFix entry problem: [{entry.ID} : {len(self.undefined_keywords)} undefined keywords]?"


    def get_user_command_and_indexes(self, command_str):
        """Parse action and indexes from a user string command for undefined keyword handling"""
        cmd, *idx_args = command_str.strip().split()
        # check if no command was submitted
        if utils.is_valid_index_list(cmd):
            if self.user_command_cache is None:
                # invalid input
                raise ValueError()
            else:
                cmd = self.user_command_cache
            idx_args = command_str.strip().split()
        else:
            # a command was specified -- parse the reset as idx args
            if not idx_args:
                # fetch all if no idxs defined
                idx_list = range(len(self.undefined_keywords))
            else:
                idx_list = [i - 1 for i in utils.get_index_list(idx_args, len(self.undefined_keywords))]
        self.user_command_cache = cmd
        return cmd, idx_list

    def parse_confirmation_response(self, command_str, entry):
        # handle the undefined keywords
        cmd, idx_args = self.get_user_command_and_indexes(command_str)
        edited_keywords = [self.undefined_keywords[i] for i in idx_args]

        if utils.matches(cmd, "keep"):
            self.resolved_keywords.extend(edited_keywords)
            self.log_message += f"Kept keyword(s) {edited_keywords}\n"
        # elif utils.matches(cmd, "change"):
        #     applied_changes = True
        #     new_kws = self.visual.ask_user("Change keywords: {} to what?".format([keywords[i] for i in idx_list]))
        #     new_kws = new_kws.strip().split()
        #     for i in idx_list:
        #         self.change_keyword(keywords[i], new_kws, index_id)
        #     keywords_final.extend(new_kws)
        elif utils.matches(cmd, "Keep-All"):
            self.resolved_keywords.extend(edited_keywords)
            self.log_message += f"Kept keyword(s) {edited_keywords}\n"
            self.decision_for_all_entries = True
        elif utils.matches(cmd, "Discard-All"):
            self.decision_for_all_entries = True
            self.log_message += f"Discarded keyword(s) {edited_keywords}\n"
        elif utils.matches(cmd, "discard"):
            self.log_message += f"Discarded keyword(s) {edited_keywords}\n"
        else:
            self.keyword_override_action = None
            raise ValueError("Invalid input.")
        # remove used up indexes
        self.undefined_keywords = list(filter(lambda x: x not in edited_keywords, self.undefined_keywords))

        if len(self.undefined_keywords) == 0:
            self.apply(entry)


    def process_keywords(self, orig_keywords):
        """Process an entity's keywords"""
        # process raw keywords
        keywords = [self.format_keyword(k) for k in orig_keywords]
        # drop empty results
        keywords = [k for k in keywords if k is not None and len(k) > 0]
        # drop discarded
        keywords = [k for k in keywords if k is not None and k not in self.discarded_keywords]
        # transform mapped
        kw = []
        for k in keywords:
            if k in self.mapped_keywords:
                kw.extend(self.mapped_keywords[k])
            else:
                kw.append(k)
        return kw