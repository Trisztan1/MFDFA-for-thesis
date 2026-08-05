import streamlit as st
import pandas as pd


def main():

    session_checks()

    st.set_page_config(
        page_title="Upload",
        page_icon="⬆️",
        layout="wide"
    )

    st.title("It tudod feltölteni és megnézni az adataidat.")

    with st.sidebar:
        # uploader button
        st.subheader("Fájl Feltöltés")
        uploaded_files = st.file_uploader(
            "Upload files",
            type="csv",
            accept_multiple_files=True,
            # key with an uploader, so every time you delete files the session key will be updated
            # and you will get a new uploader
            key=f"csv_uploader_{st.session_state.uploader_key_version}",
        )
        st.button(
            "Delete files",
            # on_click calls the reset_page_delete_files function
            on_click=reset_page_delete_files,
            # if there is no
            disabled=not bool(st.session_state.database)
        )

    if uploaded_files:
        add_to_session_state(uploaded_files)
        file_options = list(st.session_state.database.keys())

        selected_file = st.selectbox(
            label="Válaszd ki ez elemezni kívánt adatfájlt",
            options=file_options,
            index=0 if file_options else None,
            placeholder="Keres rá..."
        )

        if selected_file:
            df = st.session_state.database[selected_file]
            st.dataframe(df)
            st.success("Fájlok feltöltve.")
    else:
        st.warning("Nem töltöttél még fel semmit.")




#### ---FUNCTIONS--- ####
def session_checks():
    if "database" not in st.session_state:
        st.session_state["database"] = {}
    if "uploader_key_version" not in st.session_state:
        st.session_state["uploader_key_version"] = 0


def add_to_session_state(uploaded_files):
    for file in uploaded_files:
        if file.name not in st.session_state.database:
            st.session_state.database[file.name] = pd.read_csv(file)

def reset_page_delete_files():
    st.session_state.database.clear()
    # here you update the session state of the uploader so when you delete files you get a new uploader
    st.session_state.uploader_key_version += 1


if __name__ == "__main__":
    main()