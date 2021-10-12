# LexSAOB
Add SAOB identifiers to Wikidata Lexemes 
[Wikidata Property:P8478](https://www.wikidata.org/wiki/Property:P8478) and 
[Wikidata Property:P9963](https://www.wikidata.org/wiki/Property:P9963) 
and fall back to [Wikidata Property:P9660](https://www.wikidata.org/wiki/Property:P9660) 
if not found in the dictionary.

See [usage on Wikidata](https://w.wiki/3B7P). 

This script is maybe not that useful to run for anyone else besides the author in its current form. 
It is shared here to help others get started writing scripts to improve Wikidata.

It would be interesting to edit it to monitor the SAOB website for newly published articles/words.

This script can easily be modified to create new lexemes for every word found in the list from SAOB. 
Unfortunately that is not legal because of the database protection law.

## Thanks
Big thanks to Magnus Sälgö for reverse engineering of the SAOB website to make this possible. <3

## Requirements
* wikibaseintegrator

Install using pip:
`$ sudo pip install wikibaseintegrator

If pip fails with errors related to python 2.7 you need to upgrade your OS. 
E.g. if you are using an old version of Ubuntu like 18.04.

## Getting started
To get started install the following libraries with your package manager or
python PIP:
* wikibaseintegrator

Please create a bot password for running the script for
safety reasons here: https://www.wikidata.org/wiki/Special:BotPasswords

Copy config.example.py to config.py yourself and adjust the following
content:

username = "username"
password= "password"

# License
The code for crawling the SAOB website is not covered by license file, 
see the source URL in that file for more information.
