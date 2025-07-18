from datetime import datetime

from pydantic import BaseModel


class WikidataTimeFormat(BaseModel):
    """Takes a datetime as input and outputs the chosen precision"""
    datetime: datetime

    def day(self):
        return datetime.strftime(self.datetime, "+%Y-%m-%dT00:00:00Z/11")
