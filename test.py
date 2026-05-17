#from fugashi import Tagger
#import jaconv
#from pathlib import Path
#tagger = Tagger()

#text = "そんな気がした"

#for word in tagger(text):
#    surface = word.surface
#    pos = word.feature.pos1
#    lemma = word.feature.lemma
#    kana = word.feature.kana
#    hira = jaconv.kata2hira(kana) if kana else ""

#    print(surface, hira, pos, lemma)

import requests
import json

word = "気がする"

r = requests.get(
    "https://massif.la/ja/search",
    params={"q": word, "fmt": "json"}
)

print(json.dumps(r.json(), ensure_ascii=False, indent=2)[:3000])
