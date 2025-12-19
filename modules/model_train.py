# model_train.py - i am trying to make a model learn stuff

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
import joblib

def train_and_save_model(input_path):
    # read the file
    df = pd.read_csv(input_path)
    # drop missing rows
    df = df.dropna(subset=["headline_processed", "risk_level"])
   
    X = df["headline_processed"]
    y = df["risk_level"]
    # split again 
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    # make words into numbers
    vectorizer = TfidfVectorizer(stop_words='english')
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)
    # make the model
    model = LogisticRegression()
    model.fit(X_train_vec, y_train)
    
    y_pred = model.predict(X_test_vec)
    print("Model Evaluation:")
    print(classification_report(y_test, y_pred, zero_division=0))
    # save 
    joblib.dump(model, "model/logistic_model.pkl")
    joblib.dump(vectorizer, "model/tfidf_vectorizer.pkl")
    print("Model and vectorizer saved successfully.")

if __name__ == "__main__":
    import sys
    input_path = "data/labeled.csv"
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    train_and_save_model(input_path)

