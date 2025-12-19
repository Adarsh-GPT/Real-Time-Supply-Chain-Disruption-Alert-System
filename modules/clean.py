# clean.py

import pandas as pd
import re
import nltk
from nltk.corpus import stopwords
nltk.download('stopwords')

def clean_data(input_path):
    # read the file here
    df = pd.read_csv(input_path, encoding="latin1")
    print("Before cleaning:", df.shape)

    # drop missing headlines
    df = df.dropna(subset=["headline"])
    # drop duplicates
    df = df.drop_duplicates()
    # lowercase the headlines
    df["headline"] = df["headline"].str.lower()

    # remove links
    df["headline"] = df["headline"].apply(lambda x: re.sub(r"http\S+", "", x))
    # remove numbers
    df["headline"] = df["headline"].apply(lambda x: re.sub(r"[^a-zA-Z\s]", "", x))
    # remove extra spaces
    df["headline"] = df["headline"].apply(lambda x: re.sub(r"\s+", " ", x).strip())

    
    stop_words = set(stopwords.words("english"))
    df["headline"] = df["headline"].apply(
        lambda x: " ".join([word for word in x.split() if word not in stop_words])
    )

    print("After cleaning:", df.shape)
    return df


if __name__ == "__main__":
    import sys
    input_path = "data/finance_data.csv"
    output_path = "data/cleaned.csv"

    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    # clean and save
    df = clean_data(input_path)
    df.to_csv(output_path, index=False)
    print("Cleaned data saved to", output_path)

