from MFDFA import MFDFA
from MFDFA import fgn
import numpy as np
import pandas as pd
import streamlit as st
# from streamlit.runtime.scriptrunner import get_script_run_ctx
import plotly.express as px
import mfdfa_engine

def main():
    st.set_page_config(
        page_title="DFA",
        page_icon="📊",
        layout="wide"
    )

    st.title("It tudod megnézni az adatod ***Monofraktál*** jellegét")
    
    with st.sidebar:
        signal_generation = st.toggle("Generálj jelet")
    
    if signal_generation:
        with st.sidebar:
            st.subheader("fOU paraméterek")
            H = st.slider("Hurst H", 0.01, 0.99, 0.7,
            help="A jel perzisztenciája. 0.5 = fehér zaj, >0.5 = perzisztens. 0 és 1 között.")

            theta = st.number_input(
                "theta (mean reversion)", min_value=0.001, value=0.3,
                help="Minél nagyobb, annál erősebben húzza a folyamatot nulla felé, és annál kisebb skálán jelenik meg a törés. Bármilyen pozitív érték megadható.")

            sigma = st.sidebar.number_input("sigma (noise amplitude)", min_value=0.001, value=0.1,
            help="A véletlen lökések nagyságát szabályozza — nagyobb érték nagyobb amplitúdójú jelet ad. Bármilyen pozitív érték megadható.")

            with st.sidebar.expander("Advanced settings"):
                t_final = st.number_input("t_final", min_value=100, value=2000,
                help="A szimuláció teljes hossza (időegységben). Nagyobb érték hosszabb jelet ad.")

                delta_t = st.number_input("delta_t", min_value=0.0001, value=0.001, format="%.4f",
                help="A lépésköz (mintavételezés). Kisebb érték finomabb felbontást és pontosabb integrálást ad.")

            time, y = mfdfa_engine.generate_fou(t_final, delta_t, theta, sigma, H)
        
        st.subheader("Nyers jel")
        st.caption("A generált nyers jel az idő függvényében.")
        mfdfa_engine.plot_signal_raw(time, y)

        st.subheader("Integrált jel")
        st.caption("A jel átlagközepezett kumulatív összege — ezen fut a DFA. Zaj-szerű jelből bolyongás-szerűt csinál.")
        mfdfa_engine.plot_signal_cum_sum(y, time)
        

if __name__ == "__main__":
    main()