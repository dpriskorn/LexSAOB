from datetime import datetime

from wikibaseintegrator import wbi_datatype

from models.wikidata import WikidataTimeFormat

# This file has common statements


def time_today_statement():
    time_object = WikidataTimeFormat(datetime.today())
    return wbi_datatype.Time(
        time_object.day(),
        prop_nr="P585"
    )
