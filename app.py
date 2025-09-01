from flask import Flask, jsonify, render_template
import pandas as pd
import joblib
import os
import gspread
import atexit
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from oauth2client.service_account import ServiceAccountCredentials

import math

def clean_nans_for_json(data):
    """Recursively replaces NaN and NaT with None in dicts/lists."""
    if isinstance(data, dict):
        return {k: clean_nans_for_json(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_nans_for_json(item) for item in data]
    elif isinstance(data, float) and (math.isnan(data) or math.isinf(data)):
        return None
    else:
        return data


app = Flask(__name__)

# Paths and config
MODEL_DIR = r"D:\Project\machinehealth_3.O"
CREDENTIALS_FILE = r"D:\Project\machinehealth_3.O\machine3o-4e65656752e9.json" #json file loaction
GSCOPE = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']

timeframes = ['hourly', 'weekly', 'monthly', 'yearly']
# freq_code_map = {
#     'hourly': 'H',
#     'weekly': 'W',
#     'monthly': 'M',
#     'yearly': 'Y'
# }

freq_code_map = {
    'hourly': 'h',
    'weekly': 'W',
    'monthly': 'ME',
    'yearly': 'YE'
}



# Load models and label encoders
models = {}
encoders = {}
for tf in timeframes:
    model_path = os.path.join(MODEL_DIR, f"rf_model_{tf}.joblib")
    encoder_path = os.path.join(MODEL_DIR, f"label_encoder_{tf}.joblib")
    if os.path.exists(model_path) and os.path.exists(encoder_path):
        models[tf] = joblib.load(model_path)
        encoders[tf] = joblib.load(encoder_path)
    else:
        print(f"Warning: Model or encoder not found for {tf}")

# Load aggregated CSV
def load_aggregated_data(freq_code):
    agg_file = os.path.join(MODEL_DIR, f"aggregated_{freq_code}.csv")
    print(f"[{datetime.now()}] Loading aggregated data from: {agg_file}")
    if os.path.exists(agg_file):
        df = pd.read_csv(agg_file)
        print(f"[{datetime.now()}] Loaded {len(df)} rows.")
        return df
    print(f"[{datetime.now()}] File not found: {agg_file}")
    return None

# Load data from Google Sheets with debug prints
def load_data_from_gsheet(spreadsheet_id, sheet_name):
    try:
        print(f"[{datetime.now()}] Attempting to load data from Google Sheet: {spreadsheet_id}, sheet: {sheet_name}")
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, GSCOPE)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(spreadsheet_id)
        worksheet = sheet.worksheet(sheet_name)
        data = worksheet.get_all_records()
        print(f"[{datetime.now()}] Fetched {len(data)} rows from Google Sheets")
        df = pd.DataFrame(data)
        #df["Timestamp"] = pd.to_datetime(df["Timestamp"], dayfirst=True)
        if "Timestamp" in df.columns:
            df["Timestamp"] = pd.to_datetime(df["Timestamp"], dayfirst=True, errors='coerce')
        else:
            print("[Warning] 'Timestamp' column not found in Google Sheet. Skipping time-based operations.")


        return df
    except Exception as e:
        print(f"[{datetime.now()}] Error loading from Google Sheets: {e}")
        raise

# Clean & preprocess data
def preprocess(df):
    df.columns = [col.replace("Â", "").strip() for col in df.columns]
    
    if "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors='coerce')
        df.sort_values("Timestamp", inplace=True)
    else:
        print("[Warning] Skipping timestamp-based preprocessing (column missing)")

    df = df.dropna(subset=["MachineHealth"])
    return df

    # df.columns = [col.replace("Â", "").strip() for col in df.columns]
    # df["Timestamp"] = pd.to_datetime(df["Timestamp"])
    # df.sort_values("Timestamp", inplace=True)
    # df = df.dropna(subset=["MachineHealth"])
    # return df

# Aggregate by frequency
# def aggregate(df, freq):
#     df = df.copy()
#     df.set_index("Timestamp", inplace=True)
#     agg = df.resample(freq).agg({
#         "Temperature(°C)": ["mean", "max", "min", "std"],
#         "Humidity(%)": ["mean", "max", "min", "std"],
#         "SoundLevel(dB)": ["mean", "max", "min", "std"],
#         "MachineHealth": lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0]
#     })
#     agg.columns = ['_'.join(col).strip() for col in agg.columns.values]
#     agg.reset_index(inplace=True)
#     return agg

def aggregate(df, freq):
    if "Timestamp" not in df.columns:
        print(f"[Warning] Cannot aggregate by '{freq}' – 'Timestamp' column missing.")
        return df  # Return unaggregated data

    df = df.copy()
    df.set_index("Timestamp", inplace=True)
    # agg = df.resample(freq).agg({
    #     "Temperature(°C)": ["mean", "max", "min", "std"],
    #     "Humidity(%)": ["mean", "max", "min", "std"],
    #     "SoundLevel(dB)": ["mean", "max", "min", "std"],
    #     "MachineHealth": lambda x: x.mode().iloc[0] if not x.mode().empty else (x.iloc[0] if len(x) > 0 else "Unknown")
    # })
    agg = df.resample(freq).agg({
    "Temperature(°C)": ["mean", "max", "min", "std"],
    "Humidity(%)": ["mean", "max", "min", "std"],
    "SoundLevel(dB)": ["mean", "max", "min", "std"],
    "MachineHealth": lambda x: x.mode().iloc[0] if not x.mode().empty else (x.iloc[0] if len(x) > 0 else "Unknown")
    })

    agg.columns = ['_'.join(col).strip() for col in agg.columns.values]
    agg.reset_index(inplace=True)
    return agg

    # df = df.copy()
    # df.set_index("Timestamp", inplace=True)
    # agg = df.resample(freq).agg({
    #     "Temperature(°C)": ["mean", "max", "min", "std"],
    #     "Humidity(%)": ["mean", "max", "min", "std"],
    #     "SoundLevel(dB)": ["mean", "max", "min", "std"],
    #     "MachineHealth": lambda x: x.mode().iloc[0] if not x.mode().empty else (x.iloc[0] if len(x) > 0 else "Unknown")
    # })
    # agg.columns = ['_'.join(col).strip() for col in agg.columns.values]
    # agg.reset_index(inplace=True)
    # return agg


# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/data/<freq>')
def get_data(freq):
    freq = freq.lower()
    if freq not in timeframes:
        return jsonify({"error": "Invalid timeframe"}), 400

    freq_code = freq_code_map[freq]
    df = load_aggregated_data(freq_code)
    if df is None:
        return jsonify({"error": "Data not found"}), 404

    # return jsonify(df.to_dict(orient='records'))
    return jsonify(clean_nans_for_json(df.to_dict(orient='records')))


@app.route('/api/predict/<freq>')
def predict(freq):
    freq = freq.lower()
    if freq not in timeframes:
        return jsonify({"error": "Invalid timeframe"}), 400

    freq_code = freq_code_map[freq]
    df = load_aggregated_data(freq_code)
    if df is None:
        return jsonify({"error": "Data not found"}), 404

    model = models.get(freq)
    le = encoders.get(freq)
    if model is None or le is None:
        return jsonify({"error": "Model or encoder not loaded"}), 500

    target_col = "MachineHealth_<lambda>"
    X = df.drop(columns=["Timestamp", target_col], errors='ignore')
    X.fillna(0, inplace=True)

    preds_encoded = model.predict(X)
    preds = le.inverse_transform(preds_encoded)
    df['PredictedMachineHealth'] = preds

    df["Timestamp"] = df["Timestamp"].astype(str)
    # return jsonify(df.to_dict(orient='records'))
    return jsonify(clean_nans_for_json(df.to_dict(orient='records')))


@app.route('/api/data_gsheet')
def data_gsheet():
    SPREADSHEET_ID = '1T2v7e0T-Cd_qwZzyu8crAj8_IkjO783lH0mKBCqUIls'#id of the sheet
    SHEET_NAME = 'Sheet1'
    try:
        df = load_data_from_gsheet(SPREADSHEET_ID, SHEET_NAME)
        # df = preprocess(df)
        # agg_df = aggregate(df, 'H')  # Example: Hourly from sheet

        if "Timestamp" in df.columns:
            df = preprocess(df)
            agg_df = aggregate(df, 'H')
        else:
            print("[Warning] Timestamp missing in GSheet data. Skipping aggregation.")
            agg_df = df.copy()

        model = models.get('hourly')
        le = encoders.get('hourly')
        if model is None or le is None:
            return jsonify({"error": "Model not loaded"}), 500

        target_col = "MachineHealth_<lambda>"
        X = agg_df.drop(columns=["Timestamp", target_col], errors='ignore')
        X.fillna(0, inplace=True)

        preds_encoded = model.predict(X)
        preds = le.inverse_transform(preds_encoded)
        agg_df['PredictedMachineHealth'] = preds

        agg_df["Timestamp"] = agg_df["Timestamp"].astype(str)
        # return jsonify(agg_df.to_dict(orient='records'))
        # return jsonify(clean_nans_for_json(df.to_dict(orient='records')))
        return jsonify(clean_nans_for_json(agg_df.to_dict(orient='records')))


    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/status')
def status():
    return jsonify({
        "status": "OK",
        "models_loaded": list(models.keys())
    })

# New endpoint to check Google Sheets connection & data fetch
@app.route('/api/check_gsheet')
def check_gsheet():
    SPREADSHEET_ID = '1T2v7e0T-Cd_qwZzyu8crAj8_IkjO783lH0mKBCqUIls'
    SHEET_NAME = 'Sheet1'
    try:
        df = load_data_from_gsheet(SPREADSHEET_ID, SHEET_NAME)
        return jsonify({"status": "success", "rows_fetched": len(df)})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    
@app.route('/api/raw_gsheet')
def raw_gsheet():
    SPREADSHEET_ID = '1T2v7e0T-Cd_qwZzyu8crAj8_IkjO783lH0mKBCqUIls'
    SHEET_NAME = 'Sheet1'
    try:
        df = load_data_from_gsheet(SPREADSHEET_ID, SHEET_NAME)
        df["Timestamp"] = df["Timestamp"].astype(str)
        # return jsonify(df.to_dict(orient='records'))
        return jsonify(clean_nans_for_json(df.to_dict(orient='records')))

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/update_csv')
def update_csv():
    try:
        auto_update_aggregated_files()
        return jsonify({"status": "CSV files updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Background aggregation job
def auto_update_aggregated_files():
    try:
        SPREADSHEET_ID = '1T2v7e0T-Cd_qwZzyu8crAj8_IkjO783lH0mKBCqUIls' #id of the sheet
        SHEET_NAME = 'Sheet1'
        df = load_data_from_gsheet(SPREADSHEET_ID, SHEET_NAME)
        df = preprocess(df)
        for freq, code in freq_code_map.items():
            agg_df = aggregate(df, code)
            file_path = os.path.join(MODEL_DIR, f"aggregated_{code}.csv")
            agg_df.to_csv(file_path, index=False)
            print(f"[{datetime.now()}] Updated {file_path}")
    except Exception as e:
        print(f"[{datetime.now()}] Aggregation error: {e}")

# Scheduler setup
scheduler = BackgroundScheduler()
scheduler.add_job(auto_update_aggregated_files, 'interval', minutes=10)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


# if __name__ == '__main__':
#     app.run(debug=True)


# Quick testing suggestions:
# Run your Flask app.

# In browser or API client:

# Test CSV data:
# http://127.0.0.1:5000/api/data/hourly
# Check console for logs like:
# [2025-05-18 12:00:00] Loading aggregated data from: D:\Project\machinehealth_3.O\aggregated_H.csv

# Test Google Sheet fetch:
# http://127.0.0.1:5000/api/check_gsheet
# You should get a JSON response with status and row count.

# View raw Google Sheets data:
# http://127.0.0.1:5000/api/raw_gsheet

# Trigger CSV update:
# http://127.0.0.1:5000/api/update_csv

# Watch your Flask console for print statements confirming data loading success or errors.