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
    main_information()

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
    
    if st.session_state.database:
        file_options = list(st.session_state.database.keys())

        selected_file_name = st.selectbox(
            label="Válaszd ki ez elemezni kívánt adatfájlt",
            options=file_options,
            index=0 if file_options else None,
            placeholder="Keres rá..."
        )

        if selected_file_name:
            selected_df = st.session_state.database[selected_file_name]
            st.dataframe(selected_df)
            st.success("Fájlok feltöltve.")

            load_selected_file(selected_file_name)


    else:
        st.warning("Nem töltöttél még fel semmit.")




#### ---FUNCTIONS--- ####
def session_checks():
    if "database" not in st.session_state:
        st.session_state["database"] = {}

    if "uploader_key_version" not in st.session_state:
        st.session_state["uploader_key_version"] = 0
        
    if "selected_file" not in st.session_state:
        st.session_state["selected_file"] = None


def add_to_session_state(uploaded_files):
    for file in uploaded_files:
        if file.name not in st.session_state.database:
            st.session_state.database[file.name] = pd.read_csv(file)

def reset_page_delete_files():
    st.session_state.database.clear()
    # here you update the session state of the uploader so when you delete files you get a new uploader
    st.session_state.uploader_key_version += 1
    st.session_state.selected_file = None

def load_selected_file(selected_file_name):
    with st.sidebar:
        if st.button("Load file"):
            st.session_state.selected_file = selected_file_name
            st.session_state.analysis_started = False
            st.session_state.surrogate_test_run = False
            st.success("Fájl betöltve!")

        if st.session_state.selected_file is None:
            st.warning("Fájl nincs betöltve")
        elif st.session_state.selected_file != selected_file_name:
            st.warning(f"Kiválasztott fájl megváltozott. Kattints a 'Load file' gombra a betöltéshez!")

        if st.session_state.selected_file:
            st.info(f"Betöltött fájl: {st.session_state.selected_file}")

        st.info(f"Kiválasztott fájl: {selected_file_name}")


## MESSEGES ##

def main_information():
    st.info(
        """
        Ide csak azokat a fájlokat töltsd fel amelyeket már előre feldolgoztál. 
        Az ide feltöltött fájlok csakis **.csv** formátumban legyenek.
        A .csv fájlok csak egy oszlopot tartalmazhatnak,
        amely lényegében a jeled amelyen futtatod az analízist.
        """
    )


if __name__ == "__main__":
    main()