import re
from stopwords import stopwords


class KeyGenerator:

    def __init__(self, params=None):
        if params is None:
            pass

    def get_author_component(self, entry, lower=True):
        """Get author component for the bibtex key"""
        authorname = entry.author
        # lowercase
        if lower:
            authorname = authorname[0].lower()
        # split author names, keep first
        if "," in authorname:
            authorname = authorname.split(",")[0]
        # split the author names, keep the first author
        if "-" in authorname:
            authorname = authorname.split("-")[0]
        authorname = re.sub('[^a-zA-Z]+', '', authorname)
        return authorname

    def get_year_component(self, entry):
        return entry.year

    def get_title_component(self, entry, lower=True):
        """Get title component for the bibtex key"""
        title = entry.title
        # only keep standard alphanumerics
        if lower:
            title = title.lower()
        # remove stopwords 
        title_words = [x for x in title.strip().split() if x not in stopwords]
        # remove digits
        title_words = [x for x in title_words if not x.isdigit()]
        title = title_words[0]
        for x in ["-", "/"]:
            if x in title:
                # for dashes or slashes, keep the first part
                title = title.split(x)[0]
        title = re.sub('[^a-zA-Z0-9]+', '', title)
        return title

    def generate_key(self, entry):
        """Generate a bibtex key for the entry"""
        t = self.get_title_component(entry)
        y = self.get_year_component(entry)
        a = self.get_author_component(entry)
        generated_id = "{}{}{}".format(a, y, t)
        return generated_id
        # current_id = entry.ID
        # return current_id
        # if current_id != expected_id:
        #     # fix the ID
        #     if self.need_fix(current_id, "expected id: {}".format(expected_id)):
        #         # correct the citation id
        #         entry.set_id(expected_id)
        #         # ent.ID = expected_id
        #         # ID = expected_id
        #         fixed_entry = True
        #         return entry