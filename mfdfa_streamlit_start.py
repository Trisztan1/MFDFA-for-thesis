import streamlit as st

def main():
    ## Pages
    home = st.Page("./pages/home.py", title="Home")
    dfa = st.Page("./pages/dfa.py", title="dfa")
    mf_dfa = st.Page("./pages/mf_dfa.py", title="mf-dfa")
    upload = st.Page("./pages/upload.py", title="upload/data")

    pg = st.navigation([home, dfa, mf_dfa, upload])
    pg.run()

if __name__ == "__main__":
    main()