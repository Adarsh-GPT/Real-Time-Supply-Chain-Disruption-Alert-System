#Module 2: Text_preprocessing.py
import pandas as pd
import nltk
from nltk.stem import WordNetLemmatizer
nltk.download('punkt')
nltk.download('punkt_tab')
nltk.download('wordnet')
nltk.download('omw-1.4')

def preprocess_text(text):
    # split the text into words
    tokens = nltk.word_tokenize(text)
    # make all words small
    tokens = [t.lower() for t in tokens]
    # make words normal (like run, running -> run, delays -> delay)
    lemmatizer = WordNetLemmatizer()
    tokens = [lemmatizer.lemmatize(t) for t in tokens]
    # join words back
    return " ".join(tokens)

if __name__ == "__main__":
    import sys
    input_path = "data/cleaned.csv"
    output_path = "data/processed.csv"
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    # read the file
    df = pd.read_csv(input_path)
    df["headline"] = df["headline"].astype(str)
    # process the headlines
    df["headline_processed"] = df["headline"].apply(preprocess_text)
    # save
    df.to_csv(output_path, index=False)
    print(f"Processed data saved to {output_path}")
