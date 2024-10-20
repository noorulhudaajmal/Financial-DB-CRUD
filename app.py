import io
import json
import random
import string
import time
import uuid

import pandas as pd
import streamlit as st
from datetime import date, datetime, timezone

from pandas._libs.tslibs.parsing import DateParseError

pd.options.mode.chained_assignment = None

# -------------------------Page Config----------------------------------------
st.set_page_config(page_title="JSON Updater", layout="wide")

st.markdown("""
<style>
    .stForm{
        width: 100%;
        padding: 2rem;
        background-color: #f9f9f9;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
        border-radius: 8px;
        margin: auto;
    }
    .stExpander{
        width: 100%;
        padding: 2rem;
        background-color: #f9f9f9;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
        border-radius: 8px;
        margin: auto;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden; height:0;}
    .block-container {
      margin-top: 25px;
      padding-top: 0;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------- UI Functions --------------------------------------------

def load_json_data():
    """
    Loads the json data into dataframe and process it.
    """
    json_data = st.sidebar.file_uploader(label='Upload JSON data', type=['json', 'JSON'], accept_multiple_files=False)
    if json_data:
        data = pd.read_json(json_data)
        data['start_date'] = pd.to_datetime(data['start_date'])
        return data, json_data.name  #name of the uploaded file
    else:
        st.session_state.clear()
        return None, None


def is_valid_string(value):
    return isinstance(value, str) and bool(value.strip())


def get_selected_id(data):
    """
    get the dataset row based on the selected ID.
    """
    document_id = st.columns(4)[0].selectbox(label='Id', options=data['dataset_id'].unique(), key='document_id')
    if 'allocations' in st.session_state:
        del st.session_state['allocations']
    return data[data['dataset_id'] == document_id].iloc[0], document_id


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
        "name": '',
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
        indicator = {
            "name": st.session_state.get(f"indicator_name_{i}", ''),
            "params": st.session_state.get(f"indicator_params_{i}", []),
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



def render_form(df_row):
    """
    render the form with all widgets.
    """
    # with st.form(key='lead_form', clear_on_submit=False):
    # Initials section

    with st.expander(label="Initials", expanded=True):
        row_1 = st.columns((2, 2, 1, 1, 3))
        category_options = ["commodity", "forex", "security", "crypto"]
        category_options = list(set(category_options))
        source_options = ['yf', 'alpha_vantage', 'polygon', 'bloomberg', 'morningstar', 'iex', 'coinmarketcap', 'finnhub']
        source_options.extend([df_row['source']])
        source_options = list(set(source_options))
        # link_options = ['https://finance.yahoo.com', 'https://www.bloomberg.com', 'https://www.cnbc.com', 'https://www.marketwatch.com']
        # link_options.extend(df_row['links'])
        # link_options = list(set(link_options))
        links_str = ', '.join(df_row['links'])
        row_1[0].text_input(label="Name", value=df_row['name'], key='name')
        row_1[1].selectbox(label="Category", options=category_options, index=category_options.index(df_row['category']), key='category')
        row_1[2].text_input(label="Symbol", value=df_row['symbol'], key='symbol')
        row_1[3].selectbox(label="Source", options=source_options, index=source_options.index(df_row['source']), key='source')
        row_1[4].text_input(label="Link(s)", value=links_str, key='links')

        if f'{df_row["dataset_id"]}_allocations' not in st.session_state:
            st.session_state[f'{df_row["dataset_id"]}_allocations'] = df_row['allocations']  # Initialize allocations if not present

        st.write("##### ")
        st.write("##### Allocations")
        add_allocation = st.columns(6)[0].button("Add Allocation")
        if add_allocation:
            new_allocation = {
                "name": 'None',  # Default name
                "percentage": 0.0  # Default percentage
            }
            st.session_state[f'{df_row["dataset_id"]}_allocations'].append(new_allocation)

        allocations = st.session_state[f'{df_row["dataset_id"]}_allocations']
        row_2 = st.columns((2, 2, 3))
        for ind, alloc in enumerate(allocations):
            # Create UI components for the allocation
            row_2[0].text_input(label="Name", value=alloc['name'], key=f"allocation_{ind}_name")
            row_2[1].number_input(label="Percentage", value=alloc['percentage'], min_value=0.0, max_value=100.0, key=f"allocation_{ind}_percentage")


    # Date & Time Information
    with st.expander(label="Date & Time Information", expanded=True):
        row_1 = st.columns((2, 3, 2))
        row_1[0].date_input(label="Start Date", value=df_row['start_date'], key='start_date')
        time_interval_list = ['1h', '1d', '1w', '1mo', '3mo', '6mo', '1y']
        time_interval_list.extend(df_row['time_intervals'])
        time_interval_list = list(set(time_interval_list))
        row_1[1].multiselect(label="Time Interval", options=time_interval_list, default=df_row['time_intervals'], key='time_intervals')

        timezone_options=["America/New_York", "UTC", "Europe/London"]
        timezone_options.extend([df_row['timezone']])
        timezone_options = list(set(timezone_options))
        row_1[2].selectbox(label="Time Zone", options=timezone_options, index=timezone_options.index(df_row['timezone']), key='time_zone')

    # Data Info
    with st.expander(label="Data Info", expanded=True):
        row_1 = st.columns(8)
        column_name_options = ['open', 'close', 'high', 'low']
        column_name_options.extend([df_row['data_column_name']])
        column_name_options = list(set(column_name_options))
        api_options = ['yf', 'alpha_vantage', 'polygon']
        api_options.extend([df_row['api']])
        api_options = list(set(api_options))
        quote_options = ['USD', 'EUR', 'GBP', "GBX"]
        quote_options.extend([df_row['quote']])
        quote_options = list(set(quote_options))
        market_code_options = ['NYMEX', 'NASDAQ', 'NYSE', 'COMEX', "kraken","LSE"]
        market_code_options.extend([df_row['market_code']])
        market_code_options = list(set(market_code_options))

        cusip =  df_row.get('cusip', None)
        sedol =  df_row.get('sedol', None)
        isin =  df_row.get('isin', None)

        cusip = '' if pd.isna(cusip) else cusip
        sedol = '' if pd.isna(sedol) else sedol
        isin = '' if pd.isna(isin) else isin

        row_1[0].selectbox(label="Column", options=column_name_options, index=column_name_options.index(df_row['data_column_name']), key='data_column_name')
        row_1[1].selectbox(label="API", options=api_options, index=api_options.index(df_row['api']), key='api')
        row_1[2].text_input(label="API ID", value=df_row['api_id'], key='api_id')
        row_1[3].selectbox(label="Quote", options=quote_options, index=quote_options.index(df_row['quote']), key='quote')
        row_1[4].selectbox(label="Market Code", options=market_code_options, index=market_code_options.index(df_row['market_code']), key='market_code')
        row_1[5].text_input(label="isin", value=isin, key='isin')
        row_1[6].text_input(label="sedol", value=sedol, key='sedol')
        row_1[7].text_input(label="cusip", value=cusip, key='cusip')

    # Indicators
    st.write("---")
    st.write("### Indicators")
    render_indicators(df_row)

    st.write("---")
    btn_row = st.columns(6)
    # Submit button
    # submit_button = btn_row[0].form_submit_button(label='Update Entry')
    # drop_button = btn_row[2].form_submit_button(label="Drop Entry")
    # add_button = btn_row[4].form_submit_button(label="Add New Entry")
    submit_button = btn_row[0].button(label='Update Entry')
    drop_button = btn_row[2].button(label="Drop Entry")
    add_button = btn_row[4].button(label="Add New Entry")
    return submit_button, drop_button, add_button


def render_indicators(df_row):
    """
    Function to render the indicators section
    """

    doc_id = df_row['dataset_id']
    # names_list = ["SMA", "MACD", "ATR", "SuperTrend"]
    params_list = [f'{i}' for i in range(0, 300)]
    time_interval_list = ['1d', '1w', '1mo']

    add_indicator = st.columns(7)[6].button("Add Indicator")
    if add_indicator:
        new_indicator = {
            "name": " ",
            "params": ["1"],  # Default parameter
            "time_intervals": ["1d"],  # Default time interval
            "alerts": []  # Empty alerts list
        }
        df_row['indicators'].append(new_indicator)

    indicator_count = 0
    for i, ind in enumerate(df_row['indicators']):
        time_intervals = ind.get('time_intervals', ind.get('time_interval', []))
        time_interval_list.extend(time_intervals)
        time_interval_list = list(set(time_interval_list))

        # ind_name = ind['name']
        row_1 = st.columns((1, 3, 3, 5))
        row_1[0].text_input(label="Name", value=ind['name'], key=f"indicator_name_{i}")
        row_1[1].multiselect(label="Params", options=params_list, default=ind['params'], key=f"indicator_params_{i}")
        row_1[2].multiselect(label="Time Intervals", options=time_interval_list, default=time_intervals, key=f"indicator_intervals_{i}")

        alerts = ind.get('alerts', None)
        # If no alerts are present in 'ind', initialize it with default values
        if not alerts:
            ind['alerts'] = [{
                'condition': None,
                'trigger': None,
                'expiration': None
            }]
            alerts = ind['alerts']

        # Check if session state for alerts is initialized
        if f'alerts_{i}' not in st.session_state:
            # Populate session state with existing alerts from 'ind'
            st.session_state[f'alerts_{i}'] = alerts

        with row_1[3].expander(label="Alerts"):
            # Button to add a new alert row
            add_alert = st.button(label="Add Alert", key=f"add_{i}_alert")

            # If the button is clicked, add an empty alert to the session state
            if add_alert:
                st.session_state[f'alerts_{i}'].append({'condition': 'None', 'trigger': 'None', 'expiration': 'None'})

            # Display all alerts stored in session state
            x = 0
            for alert in st.session_state[f'alerts_{i}']:
                if all(str(value) and str(value).strip() for value in alert.values()):
                    al_row_1 = st.columns((3,3,3,2))
                    al_row_1[3].checkbox(label="Open Ended", value=alert.get('open_ended', False), key=f"{doc_id}_{i}_open_ended_{x}")
                    open_ended = st.session_state[f"{doc_id}_{i}_open_ended_{x}"]
                    al_row_1[0].text_input(label="Condition", value=alert['condition'] if alert['condition'] else "", key=f"{i}_alert_condition_{x}")
                    al_row_1[1].text_input(label="Trigger", value=alert['trigger'] if alert['trigger'] else "", key=f"{i}_alert_trigger_{x}")
                    if open_ended:
                        al_row_1[2].text_input(label="Expiration", value=alert['expiration'] if alert['expiration'] else "", key=f"{i}_alert_expiration_{x}")
                    else:
                        try:
                            alert_exp = pd.to_datetime(alert.get('expiration', pd.to_datetime(datetime.today())))
                        except Exception as e:
                            alert_exp = pd.to_datetime(datetime.today())
                        if isinstance(alert_exp, pd.Timestamp):
                            alert_exp = alert_exp.date()

                        al_row_1[2].date_input(label="Expiration", value=alert_exp, key=f"{i}_alert_expiration_{x}")

                x += 1
            st.session_state[f"ind_{i}_alert_count"] = x

        indicator_count += 1
    st.session_state[f"ind_count"] = indicator_count
            # Output for debugging
            # st.write("Session Alerts:", st.session_state[f'alerts_{i}'])



# ----------------------------------- Data Saving & Manipulations -------------------------------

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

        # st.success(f"File '{new_file_name}' is ready for download.")


def convert_timestamp_to_iso(timestamp):
    """Convert a Unix timestamp (in milliseconds) to ISO 8601 format."""
    return datetime.fromtimestamp(timestamp / 1000, timezone.utc).isoformat()


def clean_alerts(indicators):
    """Remove alert entries with null condition, trigger, and expiration."""
    for indicator in indicators:
        if 'alerts' in indicator:
            indicator['alerts'] = [
                alert for alert in indicator['alerts']
                if not (alert['condition'] is None and
                        alert['trigger'] is None and
                        alert['expiration'] is None)
            ]
            if not indicator['alerts']:
                del indicator['alerts']
    return indicators


def initialize_session_state(data):
    if 'data' not in st.session_state:
        st.session_state['data'] = data


# -------------------------------------- Main App -----------------------------------------

def main():
    """
    Main app logic
    """
    st.title("JSON Editor")
    data, json_file_name = load_json_data()
    initialize_session_state(data)

    # Check if the data has already been modified and stored in session state
    if 'data' in st.session_state and st.session_state['data'] is not None:
        data = st.session_state['data']

    if data is not None:
        try:
            df_row, document_id = get_selected_id(data)
            submit, drop, add = render_form(df_row)

            if submit:
                data = update_json_entry(data, document_id)
                st.rerun()
            if drop:
                data = data[data['dataset_id'] != document_id]
                st.session_state['data'] = data
                st.success('Entry dropped successfully!')
                time.sleep(2)
                st.rerun()
            if add:
                data = add_new_entry(data)
                time.sleep(1)
                st.rerun()

            # if st.button("Save JSON 💾"):
            save_json(file_name=json_file_name, data=st.session_state['data'])
        except IndexError as e:
            st.error("No data to display.")
        except Exception as e:
            st.error("Unexpected error occurs, check Logs.")

    else:
        st.warning("Upload Data to continue.")


if __name__ == "__main__":
    main()

