import streamlit as st
def main():
    ...


##### ---Joint MF/DFA functions--- #####

##### Sidebar Functions
def sidebar_else():
    with st.sidebar:
        st.info(f"Kiválasztott fájl: {st.session_state.selected_file}")

def analysis_button():
    # implementing an analysis button if it is true the dfa analysis of the data will begin
    with st.sidebar:
        start_analysis = st.button("Analízis megkezdése")
    
    if start_analysis:
        st.session_state.analysis_started = True

def clear_analysis():
    with st.sidebar:
        clear_analysis = st.button("Analízis törlése")

    if clear_analysis:
        st.session_state.analysis_started = False
        st.rerun()

def sidebar_sampling_rate():
    with st.sidebar:
        sampling_rate = st.number_input(
            "Sampling rate",
            min_value=1,
            step=1,
            value=150,
            help="Ide azt írd be ahány Hz-el a szemövető eszközöd operál."

        )
    
    return sampling_rate

def sidebar_step():
    with st.sidebar:
        step = st.number_input(
            "step",
            min_value=1,
            max_value=10000,
            step=1,
            value=1,
            help="Az ábra ritkítása: minden N. pontot mutatja. Nagyobb N = kevésbé részletes, de gyorsabb ábra. A DFA számítás mindig a teljes jelet használja."
        )
    
    return step

##### Other Functions
def file_check():
    if "selected_file" in st.session_state:
        if st.session_state.selected_file:
            data_df = st.session_state.database[st.session_state.selected_file]

            return data_df
    else:
        return None

def session_checks():
    if "analysis_started" not in st.session_state:
        st.session_state.analysis_started = False

if __name__ == "__main__":
    main()