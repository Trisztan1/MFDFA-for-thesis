from MFDFA import MFDFA
from MFDFA import fgn
import numpy as np
import pandas as pd
import streamlit as st
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

                step = st.number_input("")

            time, y = mfdfa_engine.generate_fou(t_final, delta_t, theta, sigma, H)

        with st.sidebar:
        # get the DFA and the Log
            st.markdown("___")
            st.subheader("DFA paraméterek")
            lag_start = st.number_input(
                "lag start (log10)", min_value=0.0, value=0.5, step=0.1, format="%.1f",
                help="A legkisebb skála, 10 hatványaként megadva (0.5 → 10^0.5 ≈ 3 minta). Ez a legkisebb ablakméret, amin a fluktuációt mérjük."
            )

            lag_stop = st.number_input(
                "lag end (log10)", min_value=lag_start+0.1, value=3.0, step=0.1, format="%.1f",
                help="A legnagyobb skála, 10 hatványaként megadva (3 → 10^3 = 1000 minta). Ne haladja meg a jel hosszának negyedét. Ha van törés a jelben, ezt érdemes bővíteni, hogy látszódjon."
            )

            lag_num = st.number_input(
                "number of lags", min_value=5, value=100, step=1,
                help="Hány skálát vizsgáljunk a start és stop között, logaritmikusan elosztva. Több pont = simább ábra, de a nagyon apró skálák egész számmá kerekítve összeolvadhatnak."
            )

            lag_mf, dfa_mf, q_list = mfdfa_engine.run_mfdfa(y, lag_start=lag_start, lag_stop=lag_stop, lag_num=lag_num)

            # here we getting the dfa
            dfa = mfdfa_engine.get_dfa(dfa_mf=dfa_mf, q_list=q_list)
        
        with st.sidebar:
            st.markdown("___")
            st.subheader("Illesztési taromány")

            fit_start = st.slider(
                "fit start (index)", min_value=0, max_value=len(lag_mf)-5, value=0,
                help="Hol kezdődjön az illesztés. Hagyd ki az apró skálák zaját a bal oldalon."
            )

            fit_end = st.slider(
                "fit end (index)", min_value=fit_start+3, max_value=len(lag_mf), value=len(lag_mf),
                help="Hol végződjön az illesztés. A nagy skálák (jobb szél) is zajosak lehetnek."
            )
            
    
        
        st.subheader("Nyers jel")
        st.caption("A generált nyers jel az idő függvényében.")
        mfdfa_engine.plot_signal_raw(time, y)

        st.subheader("Integrált jel")
        st.caption("A jel átlagközepezett kumulatív összege — ezen fut a DFA. Zaj-szerű jelből bolyongás-szerűt csinál.")
        mfdfa_engine.plot_signal_cum_sum(y, time)

        # here we get the slope, intercept and the Hurst exponent
        slope, intercept, H, r2 = mfdfa_engine.fit_dfa_exponent(lag_mf=lag_mf, dfa=dfa, fit_start=fit_start, fit_end=fit_end)

        st.subheader("Fluktuációs fügvény F(s)")
        st.caption("A fluktuáció nagysága a skála (s) függvényében, log-log skálán. Az egyenes meredeksége adja a skálázási kitevőt (a monofraktál Hurst-kitevőt).")

        mfdfa_engine.plot_fluctuation(lag=lag_mf, dfa=dfa, slope=slope, intercept=intercept, fit_start=fit_start, fit_end=fit_end)
        st.write(f"Hurst-kitevő (H) = {H:.3f}  |  R² = {r2:.4f}")
        st.caption("Az R² azt mutatja, mennyire illeszkednek a pontok az egyenesre. 1-hez közeli érték jó illesztést jelent; ha alacsony, szűkítsd az illesztési tartományt.")
    

    else:
        # this section will run when the user uploaded data

        # here we are checking st.session_state for selected data
        data_df = file_check()

        if data_df is not None:
            sidebar_else()
            start_analysis = analysis_button()

            if start_analysis:
                ...
        else:
            st.warning("Még nem töltöttél fel semmit.")
        





#### ---FUNCTIONS--- ####

def sidebar_else():
    with st.sidebar:
        st.info(f"Kiválasztott fájl: {st.session_state.selected_file}")


def file_check():
    if "selected_file" in st.session_state:
        if st.session_state.selected_file:
            data_df = st.session_state.database[st.session_state.selected_file]

            return data_df
    else:
        return None

def analysis_button():
    # implementing an analysis button if it is true the dfa analysis of the data will begin
    with st.sidebar:
        start_analysis = st.button("Analízis megkezdése")
    
    return start_analysis

        

if __name__ == "__main__":
    main()