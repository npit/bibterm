from getters.base_getter import BaseGetter


class ScholarGetter(BaseGetter):
    name = "scholar"
    def __init__(self, visual):
        super().__init__(visual)
        self.base_url = "https://scholar.google.com/scholar?hl=en&q="
