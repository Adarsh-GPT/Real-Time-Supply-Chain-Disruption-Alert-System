# 🚨 Real-Time Supply Chain Disruption Alert System
<img width="1024" height="586" alt="banner" src="https://github.com/user-attachments/assets/ca9a1cbf-5bd0-452d-94b8-8d8b034e0aca" />



A real-time NLP and Machine Learning–based system that analyzes news headlines to detect potential supply chain disruptions and classify them into business risk levels. The project combines lexicon-based sentiment analysis with supervised machine learning and presents insights through an interactive dashboard.


---

## 📌 Overview

Supply chains are highly sensitive to external events such as strikes, geopolitical tensions, natural disasters, and trade restrictions. News headlines often act as early indicators of such disruptions.

This project automatically ingests news headlines, analyzes their sentiment, maps them to risk levels, and displays the results on a secure, real-time dashboard to help businesses make faster, data-driven decisions.

---

## 🎯 Objectives

- Detect early warning signals of supply chain disruptions from news headlines  
- Classify headlines into **Low, Medium, and High Risk** categories  
- Combine rule-based sentiment analysis with machine learning for better accuracy  
- Provide an interactive and secure dashboard for real-time monitoring  

---

## 🧠 Methodology

1. **Data Ingestion**
   - Headlines collected from **NewsAPI** and **The Guardian API**
   - Historical data sourced from the **India News Headlines Dataset (Kaggle)**

2. **Text Cleaning & Preprocessing**
   - Lowercasing, URL removal, punctuation removal
   - Tokenization, stemming, and lemmatization using NLTK

3. **Sentiment Analysis & Risk Mapping**
   - VADER sentiment analysis generates compound polarity scores
   - Scores mapped to business risk levels:
     - Negative → High Risk  
     - Neutral → Medium Risk  
     - Positive → Low Risk  

4. **Machine Learning Model**
   - TF-IDF vectorization (unigrams + bigrams)
   - Logistic Regression classifier
   - Weak supervision using VADER-generated auto-labels

5. **Visualization & Deployment**
   - Interactive **Streamlit dashboard**
   - Real-time sentiment gauge and ML predictions
   - Secure authentication using **Firebase**

---

## 📊 Key Features

- Real-time headline analysis  
- Hybrid approach: VADER + Machine Learning  
- Interactive sentiment gauge visualization  
- Keyword-based headline search  
- Secure login and access control  
- Lightweight and fast model performance  

---

## 📈 Results

- Achieved ~**80% accuracy** on supply-chain–focused test data  
- Balanced precision, recall, and F1-score across classes  
- ML model captured domain-specific patterns beyond lexicon rules  
- Dashboard updates instantly without page reloads  

---

## ⚙️ Tools & Technologies

### Programming Language
- **Python**

### Libraries & Frameworks
- `pandas`, `numpy` – Data handling
- `nltk`, `vaderSentiment` – Text processing & sentiment analysis
- `scikit-learn` – TF-IDF, Logistic Regression, evaluation
- `streamlit` – Dashboard development
- `firebase_admin` – Authentication
- `requests` – API communication

### Development Environment
- **VS Code**
- **Jupyter Notebook**
- CPU-based execution (GPU optional)

---

## 🚀 How It Works (High-Level Flow)

1. Fetch latest headlines via APIs  
2. Clean and preprocess text  
3. Generate sentiment scores and risk labels  
4. Predict disruption risk using ML model  
5. Visualize insights on the Streamlit dashboard  

---

## 🔮 Future Scope

- Manual labeling for higher-quality training data  
- Multilingual news support  
- Advanced models (XGBoost, BERT, LSTM)  
- Entity-based risk analysis (ports, countries, companies)  
- Alert notifications via email or messaging platforms  

---

## 📚 References

- India Headlines News Dataset (Kaggle)  
- VADER Sentiment Analysis (Hutto & Gilbert, 2014)  
- Scikit-learn Documentation  
- NewsAPI & The Guardian Open Platform  
- Streamlit & Firebase Documentation  

---

## 👤 Author

**Adarsh (Adi) Kore**  
B.Sc. Data Science  
Aspiring Data Analyst / Data Scientist  

---

⭐ *If you find this project useful, consider giving it a star!* ⭐
