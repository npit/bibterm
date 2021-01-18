from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID, DATETIME, KEYWORD, NGRAMWORDS
from whoosh.qparser import QueryParser, MultifieldParser
from whoosh.qparser import FuzzyTermPlugin

from os import makedirs
from os.path import join

class WhooshSearcher:
    name = "whoosh"

    def update_remove(self, entry_id):
        """Remove single entry to the index"""
        wr = self.ix.writer()
        wr.delete_by_term(id, entry_id)
        wr.commit()

    def keywordize_authors(self, raw_authors):
        # treat each author name as a keyword to trigger high match score
        # others and commas
        au = [x.strip() for fullname in raw_authors for x in fullname.strip().split() if not x.startswith("others")]
        au = [x[:-1] if x[-1].endswith(",") else x for x in au]
        au = list(filter(lambda x: len(x) > 1, au))
        auth_text = ",".join(au)
        return auth_text.lower()

    def update_add(self, entry_dict, wr=None, do_commit=True):
        """Add single entry to the index"""
        if wr is None:
            wr = self.ix.writer()

        auth_text = self.keywordize_authors(entry_dict["author"])
        if "bengio" in entry_dict["ID"]:
            print(auth_text)
        kw_text = " ".join(entry_dict["keywords"]) if "keywords" in entry_dict else ""
        kw_text = kw_text.lower()
        wr.add_document(title=entry_dict["title"], id=entry_dict["ID"], year=entry_dict["year"], authors=auth_text, keywords=kw_text)
        if do_commit:
            wr.commit()

    def prepare(self, data_dict, config_dir, max_search_num, search_by_fields=None):
        """Build the index from the collection entries"""
        schema = Schema(title=TEXT, id=ID(stored=True), year=DATETIME, authors=KEYWORD, keywords=KEYWORD)
        index_dir = join(config_dir, 'index')
        makedirs(index_dir, exist_ok=True)
        self.ix = create_in(index_dir, schema)
        writer = self.ix.writer()
        for entry_dict in data_dict.values():
            self.update_add(entry_dict, wr=writer, do_commit=False)
        writer.commit()

        self.max_search_num = max_search_num
        self.search_by_fields = self.ix.schema._fields if search_by_fields is None else search_by_fields

    def search(self, raw_query):
        """Perform a search across all fields"""
        searcher = self.ix.searcher()
        parser = MultifieldParser(self.search_by_fields, self.ix.schema)
        # parser.add_plugin(FuzzyTermPlugin())
        query = parser.parse(raw_query)
        res = searcher.search(query, limit=self.max_search_num)
        results = [r['id'] for r in res]
        return results

        # ids, scores = [], []
        # # perform a search over all fields in the schema
        # for field in self.ix.schema._fields:
        #     parser = QueryParser(field, self.ix.schema)
        #     # to enable Levenshtein-based parse, use plugin
        #     query = parser.parse(raw_query)
        #     res = searcher.search(query, limit=self.max_search_num)

        #     ids.extend([r['id'] for r in res])
        #     scores.extend([s[0] for s in res.top_n])
        # searcher.close()

        # # get the best matches across all fields
        # results = sorted(zip(ids, scores), key=lambda x: x[1], reverse=True)
        # # get top K ids
        # results = [k[0] for k in results]
        # return results[:self.max_search_num]
