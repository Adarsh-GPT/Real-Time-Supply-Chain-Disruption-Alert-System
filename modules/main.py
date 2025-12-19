# main.py
import os
import pandas as pd
from clean import clean_data
from text_preprocessing import preprocess_text
from sentiment import run_sentiment
from risck_classification import add_risk_levels
import joblib
from sklearn.metrics import classification_report

# Ensure data folder exists
os.makedirs("data", exist_ok=True)

# Data Cleaning 
test_df = clean_data("data/test.csv")
test_df.to_csv("data/testing/cleaned_test.csv", index=False)

# Text Preprocessing 
test_df["headline"] = test_df["headline"].astype(str)
test_df["headline_processed"] = test_df["headline"].apply(preprocess_text)
test_df.to_csv("data/testing/processed_test.csv", index=False)

# Sentiment Analysis 
run_sentiment("data/testing/processed_test.csv", "data/testing/with_scores_test.csv")

# Risk Classification 
add_risk_levels("data/testing/with_scores_test.csv", "data/testing/labeled_test.csv")
print("Risk levels added and saved to data/testing/labeled_test.csv")

# Model Evaluation on Test data
try:
    # Load model and vectorizer
    model = joblib.load("model/logistic_model.pkl")
    vectorizer = joblib.load("model/tfidf_vectorizer.pkl")
    # Load test set
    test = pd.read_csv("data/testing/labeled_test.csv")
    test = test.dropna(subset=["headline_processed"])
    X_test = test["headline_processed"]
    y_test = test["risk_level"]
    X_test_vec = vectorizer.transform(X_test)
    y_pred = model.predict(X_test_vec)
    print("Model Evaluation on Test Set:")
    print(classification_report(y_test, y_pred, zero_division=0))
except Exception as e:
    print("Model evaluation skipped or failed:", e)

print("Test set pipeline completed successfully.")
