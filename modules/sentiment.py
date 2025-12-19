# sentiment.py 

import pandas as pd
import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer
nltk.download('vader_lexicon')

def run_sentiment(input_file, output_file):
    #loadthe file
    df = pd.read_csv(input_file)
    # VADER sentiment analyzer
    sia = SentimentIntensityAnalyzer()
    # get the score for each headline
    df["compound_score"] = df["headline_processed"].apply(lambda x: sia.polarity_scores(str(x))["compound"])
    # save
    df.to_csv(output_file, index=False)
    print("Sentiment scores saved to", output_file)

if __name__ == "__main__":
    import sys
    input_path = "data/processed.csv"
    output_path = "data/sentiment_with_scores.csv"
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    run_sentiment(input_path, output_path)
