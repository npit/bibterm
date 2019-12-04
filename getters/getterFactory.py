from getters.bibsonomy import BibsonomyGetter
from getters.gscholar import gScholarGetter
from getters.scholar import ScholarGetter
from getters.scholarly import ScholarlyGetter


class GetterFactory:

    @staticmethod
    def get_instance(name, visual):
        if name == BibsonomyGetter.name:
            return BibsonomyGetter(visual)
        elif name == ScholarlyGetter.name:
            return ScholarlyGetter(visual)
        elif name == gScholarGetter.name:
            return gScholarGetter(visual)
        elif name == ScholarGetter.name:
            return ScholarGetter(visual)
        else:
            visual.error("Undefined bibtex / pdf getter: {}".format(name))
            return None
