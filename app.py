import pandas as pd
import streamlit as st
# import mongoengine
from css.st_ui import st_ui_css
from dataset import DatasetDocument
from widgets import load_json_data, display_data_editor

pd.options.mode.chained_assignment = None

# -------------------------Page Config----------------------------------------
st.set_page_config(page_title="JSON Editor", layout="wide")
st.markdown(st_ui_css, unsafe_allow_html=True)

# -----------------------------------------------------------------------------------

def initialize_session_state(data):
    if 'data' not in st.session_state:
        st.session_state['data'] = data


def load_data_from_mongo():
    """
    Loads data from MongoDB and converts it into a DataFrame.
    """
    try:
        # Fetch all DatasetDocument objects
        datasets = DatasetDocument.objects()  # This retrieves all documents from the collection
        # Convert to JSON format
        data_list = [data.to_mongo().to_dict() for data in datasets]  # Convert to a list of dictionaries
        # Create DataFrame
        df = pd.DataFrame(data_list)
        return df
    except Exception as e:
        st.error(f"Error loading data from MongoDB: {e}")
        return None


# def main():
#     st.title("JSON Editor")
#     df = None
#     with st.sidebar:
#         if st.button("Connect to DB"):
#             logs = st.empty()
#             try:
#                 mongoengine.connect('documents', host=f"mongodb+srv://{st.secrets['username']}:{st.secrets['password']}@fin-db.837um.mongodb.net/?retryWrites=true&w=majority&appName=fin-db")
#                 logs.success("Connection successful.")
#                 df = load_data_from_mongo()
#             except Exception as e:
#                 logs.error("Connection failed.")
#
#     initialize_session_state(df)
#     if 'data' in st.session_state and st.session_state['data'] is not None:
#         df = st.session_state['data']
#
#     if df is not None:
#         # try:
#         display_data_editor(df)
#         # except Exception as e:
#         #     st.error(f"Unexpected error occured. Check Logs. {e}")
#     else:
#         st.warning("No data to view in editor.")
#
#     # except Exception as e:
#     #     st.error(f"An unexpected error occurred in the main function: {e}")


def main():
    st.title("JSON Editor")

    df, file_name = load_json_data()
    initialize_session_state(df)
    if 'data' in st.session_state and st.session_state['data'] is not None:
        df = st.session_state['data']

    if df is not None:
        try:
            display_data_editor(df)
        except Exception as e:
            st.error("Unexpected error occured. Check Logs.")
    else:
        st.warning("Upload data to use editor.")


if __name__ == "__main__":
    main()