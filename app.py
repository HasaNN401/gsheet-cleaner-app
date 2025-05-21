
with open("google-sheet-cleaner.zip", "rb") as f:
    zip_data = f.read()

st.download_button(
    label="📦 Download Full Source Code (ZIP)",
    data=zip_data,
    file_name="google-sheet-cleaner.zip",
    mime="application/zip"
)



import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
import io

st.set_page_config(page_title="Google Sheet Cleaner", layout="wide")

st.title("Google Sheet Cleaner - AppSumo Edition")
st.write("Clean messy Google Sheet data in 1 click. No coding or setup required!")

# Sidebar instructions
with st.sidebar:
    st.header("How to Use")
    st.markdown("""
    1. Go to [Google Console](https://console.cloud.google.com/)
    2. Create service account & download JSON key
    3. Share your sheet with the **client_email** from JSON
    4. Paste your Google Sheet URL below
    """)
    demo_mode = st.checkbox("Use Demo Sheet Instead")

# Input fields
if not demo_mode:
    sheet_url = st.text_input("Paste your Google Sheet URL")
    sheet_name = st.text_input("Enter Sheet Name (e.g. Sheet1)")
    creds_file = st.file_uploader("Upload your Google Credentials (JSON)", type=["json"])
else:
    # Demo settings
    sheet_url = "https://docs.google.com/spreadsheets/d/1PKkDemoSheetURL/edit"
    sheet_name = "Sheet1"
    creds_file = None

def authenticate_with_google_sheets(creds_json):
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_json, scopes=scope)
    client = gspread.authorize(creds)
    return client

def fetch_sheet_data(client, sheet_url, worksheet_name):
    sheet = client.open_by_url(sheet_url)
    worksheet = sheet.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

def clean_dataframe(df):
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df.columns = df.columns.str.title()
    df.replace(r'^\s*$', pd.NA, regex=True, inplace=True)

    if 'Email' in df.columns:
        df['Email'] = df['Email'].str.strip().str.lower()
        df['Email'] = df['Email'].str.replace(r'\.\.+', '.', regex=True)
        df['Email'] = df['Email'].str.replace(r'@+', '@', regex=True)
        df['Email'] = df['Email'].str.replace(r'\.con$', '.com', regex=True)
        df['Email'] = df['Email'].str.replace(r'(@.*)@', r'\1', regex=True)

    if 'Name' in df.columns and 'Email' in df.columns:
        df = df[df['Name'].notna() & df['Email'].notna()]
        df = df[df['Email'].str.contains(r'^[^@]+@[^@]+\.[^@]+$', na=False)]

    phone_cols = [col for col in df.columns if any(x in col.lower() for x in ['phone', 'mobile', 'contact'])]
    for col in phone_cols:
        df[col] = df[col].astype(str).str.replace(r'\D', '', regex=True)
        df = df[df[col].str.match(r'^\d{6,}$')]

    if 'Email' in df.columns:
        df = df.drop_duplicates(subset='Email')
    df = df.drop_duplicates()

    for col in df.columns:
        if df[col].dtype in ['float64', 'int64']:
            df[col].fillna(df[col].median(), inplace=True)
        elif df[col].dtype == 'object' and df[col].isnull().any():
            df[col].fillna(df[col].mode()[0], inplace=True)

    return df

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

if st.button("Clean My Sheet"):
    try:
        if not demo_mode and (not sheet_url or not sheet_name or not creds_file):
            st.error("Please fill all fields and upload credentials.")
        else:
            if demo_mode:
                creds_dict = json.loads(st.secrets["demo_credentials"])  # for your own test setup
            else:
                creds_json = creds_file.getvalue()
                creds_dict = json.loads(creds_json)

            client = authenticate_with_google_sheets(creds_dict)
            df_raw = fetch_sheet_data(client, sheet_url, sheet_name)
            df_clean = clean_dataframe(df_raw)

            st.success("✅ Cleaned Successfully! Preview below:")
            st.dataframe(df_clean)

            csv = convert_df_to_csv(df_clean)
            st.download_button("Download as CSV", data=csv, file_name="cleaned_data.csv", mime='text/csv')

    except Exception as e:
        st.error(f"Something went wrong: {e}")
