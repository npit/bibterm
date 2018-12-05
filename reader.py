from os.path import exists
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser import customization
import re

def customizations(record):
    """Use some functions delivered by the library
    :param record: a record
    :returns: -- customized record
    """
    record = customization.type(record)
    record = customization.author(record)
    record = customization.editor(record)
    record = customization.journal(record)
    record = customization.keyword(record)

    # customization for 'keywords' (plural) field
    sep=',|;'
    if "keywords" in record:
        record["keywords"] = [i.strip() for i in re.split(sep, record["keywords"].replace('\n', ''))]

    title = record["title"]
    while title[0] == "{":
        title = title[1:]
    while title[-1] == "}":
        title = title[:-1]
    record["title"] = title

    record = customization.link(record)
    record = customization.page_double_hyphen(record)
    record = customization.doi(record)
    return record


# Read bibtex file, preprocessing out comments
def read(bib_filepath):
    preprofilename = "{}.prepro".format(bib_filepath)
    outfilename = "{}.out".format(bib_filepath)

    if not exists(outfilename):
        if not exists(preprofilename):
            # preprocess
            applied_changes = False
            with open(bib_filepath) as f:
                newlines = []
                for line in f:
                    if line.startswith("%"):
                        applied_changes = True
                        continue
                    newlines.append(line)
            if applied_changes:
                with open(preprofilename, "w") as f:
                    f.writelines(newlines)
                print("Wrote preprocessed:", preprofilename)
        filename = preprofilename

    else:
        filename = outfilename

    with open(filename) as f:
        parser = BibTexParser()
        parser.customization = customizations
        content = bibtexparser.load(f, parser=parser)
        print("Loaded {} entries from {}.".format(len(content.entries), bib_filepath))
    return content

