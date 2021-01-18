from search.fuzzy_searcher import FuzzySearcher
from search.whoosh_searcher import WhooshSearcher

def create_searcher(name):
    if name == FuzzySearcher.name:
        return FuzzySearcher()
    if name == WhooshSearcher.name:
        return WhooshSearcher()
    return None
