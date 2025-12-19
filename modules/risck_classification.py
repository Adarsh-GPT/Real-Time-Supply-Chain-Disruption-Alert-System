# risck_classification.py 

import pandas as pd

def classify_risk(score):
    
    if score >= 0.05:
        return "Low"   #Positive sentiment -> Low risk
    elif score <= -0.05:
        return "High"   #Negative sentiment -> High risk
    else:
        return "Medium" #Neutral sentiment -> Medium risk

def add_risk_levels(input_path, output_path):
    df = pd.read_csv(input_path)
    # give each row a risk label
    df["risk_level"] = df["compound_score"].apply(classify_risk)
    # save 
    df.to_csv(output_path, index=False)
    print("Risk levels added and saved to", output_path)
    print(df["risk_level"].value_counts())

if __name__ == "__main__":
    import sys
    input_path = "data/sentiment_with_scores.csv"
    output_path = "data/labeled.csv"
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]
    add_risk_levels(input_path, output_path)
