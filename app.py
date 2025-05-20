import streamlit as st
import pandas as pd
import numpy as np

PASSWORD = "HasaN@"
password_input = st.text_input("Enter Access Password:", type="password")

if password_input != PASSWORD:
    st.warning("Incorrect password. Please try again.")
    st.stop()



import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import io

st.set_page_config(page_title="Google Sheet Cleaner", layout="wide")

st.title("Google Sheet Cleaner - No Code Needed")

# Step 1: Inputs from user
sheet_url = st.text_input("Google Sheet URL")
sheet_name = st.text_input("Sheet Name")
creds_file = st.file_uploader("Upload your Google Credentials JSON file", type=["json"])

def authenticate_with_google_sheets(creds_json):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(creds_json, scopes=scope)
    client = gspread.authorize(creds)
    return client

def fetch_sheet_data(client, sheet_url, worksheet_name):
    sheet = client.open_by_url(sheet_url)
    worksheet = sheet.worksheet(worksheet_name)
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

def clean_dataframe(df):
    # Column name formatting
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    df.columns = df.columns.str.title()

    # Empty string -> NA
    df.replace(r'^\s*$', pd.NA, regex=True, inplace=True)

    # Email cleaning
    if 'Email' in df.columns:
        df['Email'] = df['Email'].str.strip().str.lower()
        df['Email'] = df['Email'].str.replace(r'\.\.+', '.', regex=True)
        df['Email'] = df['Email'].str.replace(r'@+', '@', regex=True)
        df['Email'] = df['Email'].str.replace(r'\.con$', '.com', regex=True)
        df['Email'] = df['Email'].str.replace(r'(@.*)@', r'\1', regex=True)

    # Drop rows with missing Name or Email
    if 'Name' in df.columns and 'Email' in df.columns:
        df = df[df['Name'].notna() & df['Email'].notna()]
        df = df[df['Email'].str.contains(r'^[^@]+@[^@]+\.[^@]+$', na=False)]

    # Phone columns cleaning
    phone_cols = [col for col in df.columns if any(x in col.lower() for x in ['phone', 'mobile', 'contact'])]
    for col in phone_cols:
        df[col] = df[col].astype(str).str.replace(r'\D', '', regex=True)
        df = df[df[col].str.match(r'^\d{6,}$')]

    # Remove duplicates by Email
    if 'Email' in df.columns:
        df = df.drop_duplicates(subset='Email')
    df = df.drop_duplicates()

    # Fill missing numerical and categorical values
    for col in df.columns:
        if df[col].dtype in ['float64', 'int64']:
            df[col].fillna(df[col].median(), inplace=True)
        elif df[col].dtype == 'object' and df[col].isnull().any():
            df[col].fillna(df[col].mode()[0], inplace=True)

    return df

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode('utf-8')

if st.button("Clean Data"):
    if not sheet_url or not sheet_name or not creds_file:
        st.error("Please provide all inputs: Sheet URL, Sheet Name, and Credentials JSON.")
    else:
        try:
            creds_json = creds_file.getvalue()
            import json
            creds_dict = json.loads(creds_json)
            client = authenticate_with_google_sheets(creds_dict)
            df_raw = fetch_sheet_data(client, sheet_url, sheet_name)
            df_clean = clean_dataframe(df_raw)

            st.success("Data cleaned successfully! Here is a preview:")
            st.dataframe(df_clean)

            csv = convert_df_to_csv(df_clean)
            st.download_button(
                label="Download Cleaned Data as CSV",
                data=csv,
                file_name='cleaned_data.csv',
                mime='text/csv',
            )
        except Exception as e:
            st.error(f"Error: {e}")
