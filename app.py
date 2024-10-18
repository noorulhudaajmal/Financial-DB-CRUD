import io
import json
import pandas as pd
import streamlit as st
from datetime import date, datetime, timezone

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


def get_selected_id(data):
    """
    get the dataset row based on the selected ID.
    """
    document_id = st.columns(4)[0].selectbox(label='Id', options=data['dataset_id'].unique(), key='document_id')
    return data[data['dataset_id'] == document_id].iloc[0], document_id


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

    # structured JSON object based on session state
    updated_entry = {
        "dataset_id": document_id,
        "category": st.session_state.get('category', ''),
        "name": st.session_state.get('name', ''),
        "allocations":[],
        "links": st.session_state.get('links', []),
        "symbol": st.session_state.get('symbol', ''),
        "source": st.session_state.get('source', ''),
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

    # Update allocations using session state
    for i in range(len(data.iloc[row_index]['allocations'])):
        allocation = {
            "name": st.session_state.get(f"allocation_{i}_name", ''),
            "percentage": st.session_state.get(f"allocation_{i}_percentage", 0.0),
        }
        if allocation['name'] and allocation['percentage']:
            updated_entry['allocations'].append(allocation)

    # Update indicators and alerts based on session state
    for i in range(len(data.iloc[row_index]['indicators'])):
        indicator = {
            "name": st.session_state.get(f"indicator_name_{i}", ''),
            "params": st.session_state.get(f"indicator_params_{i}", []),
            "time_intervals": st.session_state.get(f"indicator_intervals_{i}", [])
        }

        # Adding alerts if they exist for the indicator
        alerts = data.iloc[row_index]['indicators'][i].get('alerts', [])
        if alerts:
            indicator_alerts = []
            for j, _ in enumerate(alerts):
                alert = {
                    "condition": st.session_state.get(f"{data.iloc[row_index]['indicators'][i]['name']}_alert_condition_{j}", ''),
                    "trigger": st.session_state.get(f"{data.iloc[row_index]['indicators'][i]['name']}_alert_trigger_{j}", ''),
                    "expiration": st.session_state.get(f"{data.iloc[row_index]['indicators'][i]['name']}_alert_expiration_{j}", '')
                }
                if all(value for value in alert.values()):
                    indicator_alerts.append(alert)
                else:
                    indicator_alerts = []
            if len(indicator_alerts)!=0:
                indicator['alerts'] = indicator_alerts
            updated_entry["indicators"].append(indicator)

    # Update the dataframe
    data.loc[row_index] = updated_entry

    # Save the updated data in session state to persist changes
    st.session_state['data'] = data.copy()
    st.success('JSON data updated successfully!')

    return st.session_state['data']  # Return the updated dataframe



def render_form(df_row):
    """
    render the form with all widgets.
    """
    with st.form(key='lead_form', clear_on_submit=False):
        # Initials section
        with st.expander(label="Initials", expanded=True):
            row_1 = st.columns((2, 2, 1, 1, 3))
            category_options = ['commodity', 'equity', 'bond', 'forex', 'cryptocurrency', 'real estate', 'ETF', 'index', 'metal']
            category_options.extend([df_row['category']])
            source_options = ['yf', 'alpha_vantage', 'polygon', 'bloomberg', 'morningstar', 'iex', 'coinmarketcap', 'finnhub']
            source_options.extend([df_row['source']])
            link_options = ['https://finance.yahoo.com', 'https://www.bloomberg.com', 'https://www.cnbc.com', 'https://www.marketwatch.com']
            link_options.extend(df_row['links'])
            row_1[0].text_input(label="Name", value=df_row['name'], key='name')
            row_1[1].selectbox(label="Category", options=category_options, index=category_options.index(df_row['category']), key='category')
            row_1[2].text_input(label="Symbol", value=df_row['symbol'], key='symbol')
            row_1[3].selectbox(label="Source", options=source_options, index=source_options.index(df_row['source']), key='source')
            row_1[4].multiselect(label="Link(s)", options=link_options, default=df_row['links'], key='links')

            st.write("##### Allocations")
            row_2 = st.columns((2,2,3))
            allocations = df_row['allocations']
            if pd.isnull(allocations):
                allocations = [{'name':None, 'percentage': 0.0}]
            ind = 0
            for alloc in allocations:
                row_2[0].text_input(label="Name", value=alloc['name'], key=f"allocation_{ind}_name")
                row_2[1].number_input(label="Percentage", value=alloc['percentage'], min_value=0.0, max_value=100.0, key=f"allocation_{ind}_percentage")
                ind +=1
        # Date & Time Information
        with st.expander(label="Date & Time Information", expanded=True):
            row_1 = st.columns((2, 3, 2))
            row_1[0].date_input(label="Start Date", value=df_row['start_date'], key='start_date')
            time_interval_list = ['1h', '1d', '1w', '1mo', '3mo', '6mo', '1y']
            time_interval_list.extend(df_row['time_intervals'])
            row_1[1].multiselect(label="Time Interval", options=time_interval_list, default=df_row['time_intervals'], key='time_intervals')
            row_1[2].text_input(label="Time Zone", value=df_row['timezone'], key='time_zone')

        # Data Info
        with st.expander(label="Data Info", expanded=True):
            row_1 = st.columns(5)
            column_name_options = ['open', 'close', 'high', 'low']
            column_name_options.extend([df_row['data_column_name']])
            api_options = ['yf', 'alpha_vantage', 'polygon']
            api_options.extend([df_row['api']])
            quote_options = ['USD', 'EUR', 'GBP']
            quote_options.extend([df_row['quote']])
            market_code_options = ['NYMEX', 'NASDAQ', 'NYSE', 'COMEX']
            market_code_options.extend([df_row['market_code']])
            row_1[0].selectbox(label="Column", options=column_name_options, index=column_name_options.index(df_row['data_column_name']), key='data_column_name')
            row_1[1].selectbox(label="API", options=api_options, index=api_options.index(df_row['api']), key='api')
            row_1[2].text_input(label="API ID", value=df_row['api_id'], key='api_id')
            row_1[3].selectbox(label="Quote", options=quote_options, index=quote_options.index(df_row['quote']), key='quote')
            row_1[4].selectbox(label="Market Code", options=market_code_options, index=market_code_options.index(df_row['market_code']), key='market_code')

        # Indicators
        st.write("---")
        st.write("##### Indicators")
        render_indicators(df_row)

        # Submit button
        submit_button = st.form_submit_button(label='Update Entry')

        return submit_button


def render_indicators(df_row):
    """
    Function to render the indicators section
    """
    params_list = [f'{i}' for i in range(0, 300)]
    time_interval_list = ['1d', '1w', '1mo']
    alert_conditions = ['Crossing', 'Trend Change', None]
    alert_triggers = ["Once Per Bar Close", None]
    alert_expiration = ["Open-ended alert", None]

    for i, ind in enumerate(df_row['indicators']):
        time_interval_list.extend(ind['time_intervals'])

        ind_name = ind['name']
        row_1 = st.columns((1, 2, 2, 3))
        row_1[0].text_input(label="Name", value=ind['name'], key=f"indicator_name_{i}")
        row_1[1].multiselect(label="Params", options=params_list, default=ind['params'], key=f"indicator_params_{i}")
        row_1[2].multiselect(label="Time Intervals", options=time_interval_list, default=ind['time_intervals'], key=f"indicator_intervals_{i}")

        alerts = ind.get('alerts', None)
        if not alerts:
            ind['alerts'] = [{
                'condition': None,
                'trigger': None,
                'expiration': None
            }]
            alerts = ind.get('alerts', None)
        with row_1[3].expander(label="Alerts"):
            if alerts:
                x = 0
                for alert in alerts:
                    alert_conditions.extend([alert['condition']])
                    alert_triggers.extend([alert['trigger']])
                    alert_expiration.extend([alert['expiration']])
                    al_row_1 = st.columns(3)
                    al_row_1[0].selectbox(label="Condition", options=alert_conditions, index=alert_conditions.index(alert['condition']), key=f"{ind_name}_alert_condition_{x}")
                    al_row_1[1].selectbox(label="Trigger", options=alert_triggers, index=alert_triggers.index(alert['trigger']), key=f"{ind_name}_alert_trigger_{x}")
                    al_row_1[2].selectbox(label="Expiration", options=alert_expiration, index=alert_expiration.index(alert['expiration']), key=f"{ind_name}_alert_expiration_{x}")
                    x += 1


# ----------------------------------- Data Saving & Manipulations -------------------------------

# def save_json(file_name, data):
#     if data is not None:
#         updated_json_str = data.to_json(orient="records")
#         updated_json = json.loads(updated_json_str)
#
#         for entry in updated_json:
#             if 'indicators' in entry:
#                 entry['indicators'] = clean_alerts(entry['indicators'])
#
#         new_file_name = f"{file_name.split('.')[0]}_updated.json"
#         with open(new_file_name, 'w') as new_json_file:
#             json.dump(updated_json, new_json_file, indent=4)
#         st.success(f"All entries saved to {new_file_name}")
#     else:
#         st.warning("Data is empty.")


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
    st.title("JSON Updater")
    data, json_file_name = load_json_data()
    initialize_session_state(data)

    # Check if the data has already been modified and stored in session state
    if 'data' in st.session_state and st.session_state['data'] is not None:
        data = st.session_state['data']

    if data is not None:
        df_row, document_id = get_selected_id(data)

        if render_form(df_row):
            data = update_json_entry(data, document_id)

        # if st.button("Save JSON 💾"):
        save_json(file_name=json_file_name, data=st.session_state['data'])
    else:
        st.warning("Upload Data to continue.")


if __name__ == "__main__":
    main()

