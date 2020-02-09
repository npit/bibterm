from getters.bibsonomy import BibsonomyGetter
from getters.gscholar import gScholarGetter
from getters.scholar import ScholarGetter
from getters.scholarly import ScholarlyGetter
from getters.scihub import ScihubGetter


class GetterFactory:

    classes = BibsonomyGetter, gScholarGetter, ScholarGetter, ScholarlyGetter, ScihubGetter

    @staticmethod
    def get_names():
        return [x.name for x in GetterFactory.classes]
    @staticmethod
    def get_instance(name, visual):
        for cls in GetterFactory.classes:
            if name == cls.name:
                return cls(visual)
        else:
            visual.error("Undefined bibtex / pdf getter: {}".format(name))
            return None
