import io
import json
import time
import uuid
import pandas as pd
import streamlit as st
from datetime import date, datetime, timezone
from operations import save_json, drop_entry, add_new_entry, update_json_entry
from utils import is_valid_string


def data_loader():
    """Loads in file by providing a file uploading widget."""
    try:
        data = st.sidebar.file_uploader(label='Upload JSON data',
                                        type=['json', 'JSON'],
                                        accept_multiple_files=False)
        return data
    except json.JSONDecodeError:
        st.error("The file is not a valid JSON. Please check the file format.")
        return None, None
    except ValueError:
        st.error("File contains invalid JSON structure.")
        return None
    except FileNotFoundError:
        st.error("No file was found. Please upload a valid file.")
        return None, None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None, None



def load_json_data():
    """
    Loads the json data into dataframe and process it.
    """
    file = data_loader()  # load the file
    if file:
        try:
            # Try to read the file as JSON
            data = pd.read_json(file)
            try:
                # Try to parse 'start_date' to datetime
                data['start_date'] = pd.to_datetime(data['start_date'])
            except KeyError as e:
                st.error("'start_date' column not found in the data.")
                return None, None
            except pd.errors.OutOfBoundsDatetime as e:
                st.error("Invalid date format in 'start_date'. Please ensure dates are correct.")
                return None, None
            except Exception as e:
                st.error(f"An unexpected error occurred while parsing dates: {e}")
                return None, None

            return data, file.name
        except ValueError as e:
            st.error("Error reading the file. Please upload a valid JSON file.")
            return None, None

    else:
        st.session_state.clear()
        return None, None




@st.dialog("Edit Record", width="large")
def open_editor_dialog(data, doc_id):
    df_row = data[data['dataset_id'] == doc_id].iloc[0]
    with st.expander(label="Initials", expanded=True):
        row_1 = st.columns((2, 2, 1, 1, 3))
        category_options = ["commodity", "forex", "security", "crypto"]
        category_options = list(set(category_options))
        source_options = ['yf', 'alpha_vantage', 'polygon', 'bloomberg', 'morningstar', 'iex', 'coinmarketcap', 'finnhub']
        source_options.extend([df_row['source']])
        source_options = list(set(source_options))
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
    submit_button = btn_row[0].button(label='Update Entry')
    if submit_button:
        data = update_json_entry(data, doc_id)
        st.rerun()
    # return submit_button


def render_indicators(df_row):
    """
    Function to render the indicators section
    """

    counter = 0
    doc_id = df_row['dataset_id']
    time_interval_list = ['1d', '1w', '1mo']

    add_indicator = st.columns(7)[6].button("Add Indicator")
    if add_indicator:
        new_indicator = {
            "name": " ",
            "params": ["1"],
            "time_intervals": ["1d"],
            "alerts": []
        }
        df_row['indicators'].append(new_indicator)

    # initializing 'indicators' not in st.session_state:
    st.session_state['indicators'] = []

    for i in range(len(df_row['indicators']) - 1, -1, -1):
        ind = df_row['indicators'][i]
        alerts = ind.get('alerts', [])

        # If no alerts are present in 'ind', initialize it with default values
        if len(alerts)==0:
            df_row['indicators'][i]["alerts"] = alerts

        row_1 = st.columns((1, 2, 3, 5,1))
        place_holder = row_1[4].empty()
        drop = place_holder.button(label="🗑️", key=f"indicator_drop_btn_{i}")
        if drop:
            del df_row['indicators'][i]
            place_holder.empty()
            continue

        ind_params = ', '.join(ind['params'])
        time_intervals = ind.get('time_intervals', ind.get('time_interval', []))
        time_interval_list.extend(time_intervals)
        time_interval_list = list(set(time_interval_list))


        row_1[0].text_input(label="Name", value=ind['name'], key=f"indicator_name_{i}")
        row_1[1].text_input(label="Params", value=ind_params, key=f"indicator_params_{i}")
        row_1[2].multiselect(label="Time Intervals", options=time_interval_list, default=time_intervals, key=f"indicator_intervals_{i}")

        ind_alerts = []
        with row_1[3].expander(label="Alerts"):
            add_alert = st.button(label="Add Alert", key=f"add_{i}_alert")
            if add_alert:
                alerts.append({'condition': 'None', 'trigger': 'None', 'expiration': 'None'})
                # df_row['indicators'][i]["alerts"].append({'condition': 'None', 'trigger': 'None', 'expiration': 'None'})

            x = 0
            for al_ind in range(len(alerts)):
                alert = alerts[al_ind]
                if all(str(value) and str(value).strip() for value in alert.values()):
                    al_row_1 = st.columns((3,3,3,2,1))
                    alert_place_holder = al_row_1[4].empty()
                    drop_alert = alert_place_holder.button(label="🗑️", key=f"ind_{i}_alert_drop_btn_{x}")
                    if drop_alert:
                        alerts[al_ind] = None
                        alert_place_holder.empty()
                        x += 1
                        continue

                    al_row_1[3].checkbox(label="Open", value=alert.get('open_ended', False), key=f"{doc_id}_{i}_open_ended_{x}")
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
                    ind_alerts.append(alert)
                x += 1
                counter += 1
            st.session_state[f"ind_{i}_alert_count"] = x

        ind['alerts'] = ind_alerts

        if is_valid_string(ind['name']):
            st.session_state['indicators'].insert(0, ind)



def display_filters(data):
    filters = st.columns(3)
    dataset_ids = filters[0].multiselect(label="ID(s)", options=data['dataset_id'].unique(), placeholder="All")
    if not dataset_ids:
        dataset_ids = data['dataset_id'].unique()
    filtered_data = data[data['dataset_id'].isin(dataset_ids)]

    stock_categories = filters[1].multiselect(label="Categories", options=filtered_data['category'].unique(), placeholder="All")
    if not stock_categories:
        stock_categories = filtered_data['category'].unique()
    filtered_data = filtered_data[filtered_data['category'].isin(stock_categories)]

    stock_symbols = filters[2].multiselect(label="Symbol(s)", options=filtered_data['symbol'].unique(), placeholder="All")
    if not stock_symbols:
        stock_symbols = filtered_data['symbol'].unique()
    filtered_data = filtered_data[filtered_data['symbol'].isin(stock_symbols)]

    return filtered_data



def display_data_editor(data):
    data = display_filters(data)
    add = st.columns(8)[7].button(label="➕", help="Add new entry to the data.")
    if add:
        data = add_new_entry(data)
        time.sleep(0.1)
        st.rerun()

    for ind, row in data.iterrows():
        doc_id = row["dataset_id"]
        if ind==0:
            labels = "visible"
        else:
            labels = "collapsed"
        with st.form(key=f"row-{ind}-edit", border=False):
            doc_fields = st.columns((4,4,2,2,2,1,1))
            doc_fields[0].text_input(label="ID", value=row["dataset_id"], disabled=True, label_visibility=labels)
            doc_fields[1].text_input(label="Name", value=row["name"], label_visibility=labels)
            doc_fields[2].text_input(label="Category", value=row["category"], label_visibility=labels)
            doc_fields[3].text_input(label="Symbol", value=row["symbol"], label_visibility=labels)
            doc_fields[4].date_input(label="Start Date", value=row["start_date"], label_visibility=labels)
            edit = doc_fields[5].form_submit_button("✏️", help="Edit entry data.")
            drop = doc_fields[6].form_submit_button("🗑️", help="Drop entry.")
            if edit:
                open_editor_dialog(data, doc_id)
            if drop:
                drop_entry(data, doc_id)

    save_json(file_name="edited.json", data=st.session_state['data'])
