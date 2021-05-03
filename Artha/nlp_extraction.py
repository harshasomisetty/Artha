import spacy
from spacy.tokens import Doc
import json
# import Artha.data_process as dp
from datetime import datetime
# import numpy as np
from tqdm import tqdm

from spacy.tokens import DocBin
# from spacytextblob.spacytextblob import SpacyTextBlob
# from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
# analyzer = SentimentIntensityAnalyzer()

ent_lab = ["ORG", "NORP", "MONEY"]

config = {
    # "phrase_matcher_attr": "LOWER",
    # "validate": True,
    "overwrite_ents": True
}

with open("../data/binance_tickers.json", "r") as w:
    crypto_ticks = json.loads(w.read())

nlp = spacy.load("en_core_web_sm")

ruler = nlp.add_pipe("entity_ruler", config=config, after="ner")
ruler.from_disk("../data/binance_patterns.jsonl")

# nlp.add_pipe('spacytextblob')


def _get_crypto_tickers(doc):
    ignore = ['ath', 'just', 'add', 'pdf', 'band',
              'ramp', 'salt', 'nft', 'rss', 'iq',
              'triggers', 'og', 'win', 'auto']

    tickers = [ent.text.strip() for ent in doc.ents
               if ent.label_ in ent_lab and ent.text.lower() not in ignore]
    # tickers = [tick for tick in tickers if tick not in ignore]

    final_tickers = []
    for cur in tickers:

        if cur in crypto_ticks.values():
            final_tickers.append(cur)

        elif cur.lower() in crypto_ticks.keys():
            final_tickers.append(crypto_ticks[cur.lower()].upper())

    return list(set(final_tickers))


Doc.set_extension("tickers", getter=_get_crypto_tickers)
Doc.set_extension("tweet_id", default=False)
Doc.set_extension("tweeted_at", default=False)
Doc.set_extension("username", default=False)


def run_pipeline(tweet_text):
    docs = []
    with nlp.select_pipes(disable=["tagger", "parser", "lemmatizer"]):
        for doc, context in tqdm(nlp.pipe(tweet_text,
                                          as_tuples=True,
                                          n_process=-1)):

            if doc._.tickers:
                doc._.tweet_id = context["id"]
                doc._.username = context["username"]
                try:
                    doc._.tweeted_at = datetime.strftime(
                        datetime.strptime(context["created_at"],
                                          '%a %b %d %H:%M:%S +0000 %Y'),
                        '%m/%d/%Y %H:%M:%S')
                    docs.append(doc)
                except ValueError:
                    doc._.tweeted_at = datetime.strftime(
                        datetime.strptime(context["created_at"][:-5],
                                          "%Y-%m-%dT%H:%M:%S"),
                        '%m/%d/%Y %H:%M:%S')
                    docs.append(doc)

    return docs


def save_backup(docs, location="backup.txt"):
    doc_bin = DocBin(attrs=["ENT_IOB", "ENT_TYPE"], store_user_data=True)
    for doc in tqdm(docs):
        doc_bin.add(doc)
    with open(location, "wb") as f:
        f.write(doc_bin.to_bytes())
    print("saved")


def load_backup(location="backup.txt"):
    with open(location, "rb") as f:
        doc_bin = DocBin().from_bytes(f.read())
        print("loaded")
        return list(doc_bin.get_docs(nlp.vocab))
