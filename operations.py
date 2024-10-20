import io
import json
import time
import uuid
import pandas as pd
import streamlit as st
from datetime import date, datetime, timezone
from utils import is_valid_string, clean_alerts, convert_timestamp_to_iso


def add_new_entry(data):
    """
    Add a new entry with blank fields and a random ID.
    """
    new_id = str(uuid.uuid4())

    default_date = datetime.strptime("2020/01/01", "%Y/%m/%d")
    default_date_utc = default_date.replace(tzinfo=timezone.utc)

    blank_entry = {
        "dataset_id": new_id,
        "category": "commodity",
        "name": 'Sample Stock',
        "allocations": [{
            'name':None,
            'percentage':0.0
        }],
        "links": ["https://finance.yahoo.com"],
        "symbol": '',
        "source": 'yf',
        "isin":'',
        "cusip":'',
        "sedol":'',
        "start_date": default_date_utc.isoformat(),
        "time_intervals": ['1d', '1h'],
        "timezone": 'America/New_York',
        "data_column_name": 'close',
        "api": 'yf',
        "api_id": '',
        "quote": 'USD',
        "market_code": 'NYMEX',
        "indicators": [
        ]
    }
    new_record = pd.DataFrame([blank_entry])
    new_record['start_date'] = pd.to_datetime(new_record['start_date'])
    data = pd.concat([new_record, data], ignore_index=True)
    st.session_state['data'] = data
    st.success('New entry added successfully with default values!')
    return data


def update_json_entry(data, document_id):
    """
    Handle form submission and update JSON data based on session state.
    """
    # index of the row that matches the document_id
    row_index = data[data['dataset_id'] == document_id].index[0]

    def serialize_value(value):
        """
        Helper function to handle date serialization.
        """
        if isinstance(value, date):
            return value.isoformat()
        return value

    input_links = st.session_state.get('links', '')
    # structured JSON object based on session state
    updated_entry = {
        "dataset_id": document_id,
        "category": st.session_state.get('category', ''),
        "name": st.session_state.get('name', ''),
        "allocations":[],
        "links":[link.strip() for link in input_links.split(',')] if input_links else [],
        "symbol": st.session_state.get('symbol', ''),
        "source": st.session_state.get('source', ''),
        "isin":st.session_state.get('isin', ''),
        "cusip":st.session_state.get('cusip', ''),
        "sedol":st.session_state.get('sedol', ''),
        "start_date": serialize_value(st.session_state.get('start_date', '')),
        "time_intervals": st.session_state.get('time_intervals', []),
        "timezone": st.session_state.get('time_zone', ''),
        "data_column_name": st.session_state.get('data_column_name', ''),
        "api": st.session_state.get('api', ''),
        "api_id": st.session_state.get('api_id', ''),
        "quote": st.session_state.get('quote', ''),
        "market_code": st.session_state.get('market_code', ''),
        "indicators": []
    }

    for var in ["isin", "cusip", "sedol"]:
        if not is_valid_string(updated_entry[var]):
            del updated_entry[var]

    # Update allocations using session state
    for i in range(len(st.session_state[f'{document_id}_allocations'])):
        allocation = {
            "name": st.session_state.get(f"allocation_{i}_name", ''),
            "percentage": st.session_state.get(f"allocation_{i}_percentage", 0.0),
        }
        if allocation['name'] and allocation['percentage']:
            updated_entry['allocations'].append(allocation)


    # Update indicators and alerts based on session state
    for i in range(st.session_state['ind_count']):
        ind_params = st.session_state.get(f"indicator_params_{i}", [])
        indicator = {
            "name": st.session_state.get(f"indicator_name_{i}", ''),
            "params": [x.strip() for x in ind_params.split(',') if x.strip()],
            "time_intervals": st.session_state.get(f"indicator_intervals_{i}", [])
        }

        if not is_valid_string(indicator['name']):
            continue

        # Adding alerts if they exist for the indicator
        # alerts = data.iloc[row_index]['indicators'][i].get('alerts', [])


        alerts = st.session_state[f"alerts_{i}"]
        if alerts:
            indicator_alerts = []
            for j, _ in enumerate(alerts):
                status = st.session_state.get(f"{document_id}_{i}_open_ended_{j}", False)
                if status:
                    alert = {
                        "condition": st.session_state.get(f"{i}_alert_condition_{j}", ''),
                        "trigger": st.session_state.get(f"{i}_alert_trigger_{j}", ''),
                        "expiration": st.session_state.get(f"{i}_alert_expiration_{j}", ''),
                        "open_ended": "True"
                    }
                else:
                    expiration_date = st.session_state.get(f"{i}_alert_expiration_{j}", '')
                    if not expiration_date:
                        expiration_date = datetime.today()
                    expiration_iso_format = expiration_date.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                    alert = {
                        "condition": st.session_state.get(f"{i}_alert_condition_{j}", ''),
                        "trigger": st.session_state.get(f"{i}_alert_trigger_{j}", ''),
                        "expiration": expiration_iso_format,
                    }
                if all(str(value) and str(value).strip() for value in alert.values()):
                    indicator_alerts.append(alert)
                else:
                    indicator_alerts = []
            if len(indicator_alerts)!=0:
                indicator['alerts'] = indicator_alerts
            updated_entry["indicators"].append(indicator)
        st.session_state[f"alerts_{i}"] = None
        del st.session_state[f"alerts_{i}"]

    # Update the dataframe
    data.loc[row_index] = updated_entry

    # Save the updated data in session state to persist changes
    st.session_state['data'] = data.copy()
    del st.session_state['ind_count']
    del st.session_state[f'{document_id}_allocations']
    st.success('JSON data updated successfully!')

    return st.session_state['data']  # Return the updated dataframe


def drop_entry(data, doc_id):
    data = data[data['dataset_id'] != doc_id]
    st.session_state['data'] = data
    st.rerun()


def save_json(file_name, data):
    if data is not None:
        updated_json_str = data.to_json(orient="records")
        updated_json = json.loads(updated_json_str)

        # Clean the alerts
        for entry in updated_json:
            if 'start_date' in entry and isinstance(entry['start_date'], int):
                entry['start_date'] = convert_timestamp_to_iso(entry['start_date'])

            if 'indicators' in entry:
                entry['indicators'] = clean_alerts(entry['indicators'])

            for var in ["isin", "cusip", "sedol"]:
                if var in entry.keys():
                    if not is_valid_string(entry[var]):
                        del entry[var]

        # Convert cleaned data to JSON string
        cleaned_json_str = json.dumps(updated_json, indent=4)

        # Create an in-memory file
        new_file_name = f"{file_name.split('.')[0]}_updated.json"
        json_file_io = io.StringIO(cleaned_json_str)

        # Provide a download button in Streamlit
        st.download_button(
            label="Download JSON file 💾",
            data=json_file_io.getvalue(),
            file_name=new_file_name,
            mime="application/json"
        )