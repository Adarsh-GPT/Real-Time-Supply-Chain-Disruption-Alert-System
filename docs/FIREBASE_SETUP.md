# Firebase Setup Guide (Streamlit Architecture)

SupplyRadar can run entirely in "Demo Mode" without Firebase. However, to enable persistent user accounts, saved watchlists, and historical article search, you must connect it to a free Firebase project.

## 1. Create a Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Click **Add project** → name it (e.g. `supply-radar-alerts`)
3. Disable Google Analytics (not needed) → **Create project**

---

## 2. Enable Authentication (Email/Password)

Because Streamlit Cloud doesn't easily support complex OAuth redirects without extra libraries, we use the Firebase REST API for simple Email/Password auth.

1. In the left menu, click **Build** → **Authentication**.
2. Click **Get Started**.
3. Go to the **Sign-in method** tab.
4. Click **Email/Password** and enable the first toggle. Click **Save**.

---

## 3. Enable Firestore Database

1. In the left menu, click **Build** → **Firestore Database**.
2. Click **Create database**.
3. Select **Start in production mode** (or test mode, our Admin SDK bypasses rules anyway).
4. Choose a region close to your users (e.g. `us-central`, `europe-west`).
5. Click **Enable**.

---

## 4. Get Your Credentials

You need 3 things for your `.env` file.

### A. Firebase Web API Key
1. Go to **Project Settings** (the gear icon at the top left) → **General** tab.
2. Look for **Web API Key**. Copy this value.
3. Paste it into your `.env` as `FIREBASE_API_KEY=...`

### B. Project ID
1. On that same **General** tab, look for **Project ID**.
2. Paste it into your `.env` as `FIREBASE_PROJECT_ID=...`

### C. Service Account JSON (For Admin SDK)
1. Still in **Project Settings**, go to the **Service accounts** tab.
2. Click the **Generate new private key** button at the bottom.
3. Download the JSON file.
4. Move this file into the root folder of your project (where `app.py` is) and rename it exactly to: **`firebase-credentials.json`**
*(Note: This file is in `.gitignore` so it will never be accidentally uploaded to GitHub).*

---

## 5. Final `.env` Configuration

Your `.env` file should now look like this:

```env
FIREBASE_API_KEY=AIzaSyB... (your web api key)
FIREBASE_PROJECT_ID=supply-radar-12345
FIREBASE_CREDENTIALS_PATH=firebase-credentials.json
```

## 6. Test It Out

Restart your Streamlit server:
```bash
streamlit run app.py
```

The "Try Demo Mode" button will disappear, and you must now Register an account. Once registered, your user profile, watchlist, and any news fetched will be permanently saved to your new Firestore database!
