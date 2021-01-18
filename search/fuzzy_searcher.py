import os
import pickle
from search.searcher import Searcher
from fuzzywuzzy import fuzz


class FuzzySearcher(Searcher):
    name = "fuzzy"

    def __init__(self):
        self.fuzzy_score_match_threshold = 50
        self.stopwords = """i me my myself we our ours ourselves you you're you've you'll you'd your yours yourself yourselves he him his himself she she's her hers herself it it's its itself they them their theirs themselves what which who whom this that that'll these those am is are was were be been being have has had having do does did doing a an the and but if or because as until while of at by for with about against between into through during before after above below to from up down in out on off over under again further then once here there when where why how all any both each few more most other some such no nor not only own same so than too very s t can will just don don't should should've now d ll m o re ve y ain aren aren't couldn couldn't didn didn't doesn doesn't hadn hadn't hasn hasn't haven haven't isn isn't ma mightn mightn't mustn mustn't needn needn't shan shan't shouldn shouldn't wasn wasn't weren weren't won won't wouldn wouldn't""".split()

        # search settings


    def prepare(self, data_dict, config_dir, max_search_num, searchable_fields=None):
        self.searchable_fields=searchable_fields
        self.max_search_num = max_search_num
        self.data = list(data_dict.values())
        self.multivalue_keys = ["author", "keywords"]

    def is_multivalue_key(self, filter_key):
        return filter_key in self.multivalue_keys


    def preprocess_query(self, query):
        query = query.lower()
        query = " ".join([q for q in query.split() if q not in self.stopwords])
        return query

    def fuzzy_search(self, query, candidates, iterable_items=False):
        query = self.preprocess_query(query)
        if iterable_items:
            # flatten
            nums = list(map(len, candidates))
            flattened_candidates = [c for clist in candidates for c in clist]
            # score
            raw_results = [(c, fuzz.partial_ratio(query, c)) for c in flattened_candidates]
            # argmax
            results, curr_idx = [], 0
            for n in nums:
                if n > 1:
                    max_val = max(raw_results[curr_idx: curr_idx + n], key=lambda x: x[1])
                else:
                    max_val = raw_results[curr_idx]
                results.append(max_val)
                # print("Got from: {} : {}".format(raw_results[curr_idx: curr_idx + n], max_val))
                curr_idx += n
        else:
            results = [(c, fuzz.partial_ratio(query, c)) for c in candidates]
        # assign index
        results = [(results[i], i) for i in range(len(results)) if results[i][1] >= self.fuzzy_score_match_threshold]
        results = sorted(results, key=lambda x: x[0][1], reverse=True)
        return results[:self.max_search_num]


    def search(self, query):
        """Launch a search to the entry collection
        """
        if not query:
            return []
        results_ids, match_scores = [], []
        # perform the search on all searchable fields
        for field in self.searchable_fields:
            # self.visual.debug(f"Searching field {field} for {query}")
            res = self.filter_entry_by_key(field, query, reference_entries=self.data)
            ids, scores = [r[0] for r in res], [r[1] for r in res]
            for i in range(len(ids)):
                if ids[i] in results_ids:
                    existing_idx = results_ids.index(ids[i])
                    # replace score, if it's higher
                    if scores[i] > match_scores[existing_idx]:
                        match_scores[existing_idx] = scores[i]
                else:
                    # if not there, just append
                    results_ids.append(ids[i])
                    match_scores.append(scores[i])

        results_ids = sorted(zip(results_ids, match_scores), key=lambda x: x[1], reverse=True)
        # apply max search results filtering
        results_ids = results_ids[:self.max_search_num]
        results_ids, match_scores = [r[0] for r in results_ids], [r[1] for r in results_ids]

        return results_ids

    def filter_entry_by_key(self, filter_key, filter_value, reference_entries):
        if filter_key not in self.searchable_fields:
            self.visual.warn("Must filter with a key in: {}".format(self.searchable_fields))
            return
        candidate_values = []
        searched_entry_ids = []
        # get candidate values, as key to a value: entry_id dict
        for entry_dict in reference_entries:
            eid = entry_dict["ID"]
            try:
                value = entry_dict[filter_key]
            except KeyError:
                continue
            if value is None or len(value) == 0:
                continue

            if type(value) == str:
                value = value.lower()
            searched_entry_ids.append(eid)
            candidate_values.append(value)

        # search and return ids of results
        res = self.fuzzy_search(filter_value, candidate_values, self.is_multivalue_key(filter_key))
        if filter_key == "ID":
            # return the IDs
            return [r[0] for r in res]
        elif filter_key == "title":
            # get ids
            res_ids, scores  = [], []

            for t in res:
                (title, idx), score = t
                res_ids.append(reference_entries[idx]["ID"])
                scores.append(score)
            return list(zip(res_ids, scores))
        elif self.is_multivalue_key(filter_key):
            # limit results per keyword
            res = [(searched_entry_ids[r[1]], r[0][1]) for r in res]
        return res
