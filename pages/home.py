import streamlit as st

def main():
    st.set_page_config(
    page_title="MF-DFA",
    page_icon="📊",
    layout="wide"
    )
  
    # Title and intro
    st.title("MF_DFA Analízis")
    st.write("**Üdvözöllek!**")
    st.write("Ennek az appnak a segítaégével MF-DFA analízist végezhetsz az adataidon.")
    st.header("Mi is az az MFDFA?")

if __name__ == "__main__":
    main()