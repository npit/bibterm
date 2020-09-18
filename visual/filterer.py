import operator

operators = {
    "=": operator.eq,
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
    "!=": operator.ne,
    "sw": lambda x, y: x.startswith(y),
    "ew": lambda x, y: x.endswith(y)
}

class Filter:
    # which operand corresponds to an entry lambda function
    entry_lambda_index = None
    def add_constant(self, const):
        self.constant = const
    def add_lambda_func(self, lam):
        self.lambda_func = lam
    def set_operator(self, op):
        self.operator = op
    def satisfied_by(self, entry):
        operands = [self.lambda_func(entry), self.constant]
        if self.entry_lambda_index == 1:
            operands = list(reversed(operands))
        for i in range(len(operands)):
            if type(operands[i]) == str:
                operands[i] = operands[i].lower()
        passes = self.operator(*operands)
        return passes

class Filterer:
    delimiter = ","

    def __init__(self, vis, entry_keys):
        self.visual = vis
        self.entry_keys = entry_keys

    def get_key_and_value(self, keyval):
        key, value = None, None
        for data in keyval:
            data = data.strip()
            # value: quotes or numerics
            if any(x in data for x in ['"', "'"]) or any(x.isdigit() for x in data):
                value = data
                break
            # key: reserved words
            if any(x == data for x in self.entry_keys):
                key = data
                break
        if key is not None:
            value = [x for x in keyval if x != key][0]
        elif value is not None:
            key = [x for x in keyval if x != value][0]
        return key, value

    def parse_filters(self, filters_str):
        """Parse a string to multiple filters"""
        filters = []
        for filt_str in filters_str.split(self.delimiter):
            try:
                operator_str = [x for x in operators if x in filt_str][0]
                operands = [x.strip() for x in filt_str.split(operator_str)]
                key, value = self.get_key_and_value(operands)
                operator = operators[operator_str]
                filt = Filter()
                filt.add_constant(value)
                filt.set_operator(operator)
                filt.add_lambda_func(lambda ent: ent.get_value(key))
                
                filt.entry_lambda_index = operands.index(key)

                filters.append(filt)
            except IndexError:
                raise ValueError(f"Invalid filter string {filt_str}")
                break
        return filters
                

    def apply_filters(self, filters_str, entries):
        try:
            filters = self.parse_filters(filters_str)
            for filt in filters:
                entries = [e for e in entries if filt.satisfied_by(e)]
            return entries
        except ValueError as p:
            self.visual.error(f"{p}")
            self.visual.error(f"Available filters: {list(operators.keys())} entry keys: {self.entry_keys}")
            return
