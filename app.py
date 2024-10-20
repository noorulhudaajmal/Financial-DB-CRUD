import pandas as pd
import streamlit as st

from css.st_ui import st_ui_css
from widgets import load_json_data, display_data_editor

pd.options.mode.chained_assignment = None

# -------------------------Page Config----------------------------------------
st.set_page_config(page_title="JSON Editor", layout="wide")
st.markdown(st_ui_css, unsafe_allow_html=True)

# -----------------------------------------------------------------------------------

def initialize_session_state(data):
    if 'data' not in st.session_state:
        st.session_state['data'] = data


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