from MFDFA import MFDFA
from MFDFA import fgn
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import mfdfa_engine


def main():
    st.set_page_config(
        page_title="MF-DFA",
        page_icon="📊",
        layout="wide"
    )

    st.title("It tudod megnézni az adatod ***Multifraktál*** jellegét")

    with st.sidebar:
        signal_generation = st.toggle("Generálj jelet")

    if signal_generation:
        with st.sidebar:
            st.subheader("Binomial cascade Paraméterek")
            n_levels = st.number_input(
                "number of levels", min_value=10, max_value=20, value=14,
                help="A kaszkád szintjeinek száma. A jel hossza 2^n_levels lesz (pl. 14 → 16384 pont). Több szint = hosszabb, megbízhatóbb jel, de lassabb számítás."
            )

            p = st.slider(
                "p (split fraction)", min_value=0.01, max_value=0.99, value=0.25,
                help="A tömeg megosztási aránya minden osztásnál. p=0.5 → egyenletes (monofraktál). Minél távolabb 0.5-től, annál szélesebb a multifraktál spektrum."
            )

            seed = st.number_input(
                "seed (random)", min_value=0, value=0,
                help="A véletlengenerátor magja. Ugyanaz a mag ugyanazt a jelet adja — az ismételhetőséghez hasznos."
            )
        
        # making the multifractal signal
        measure, time = mfdfa_engine.binomial_cascade(n_levels=n_levels, p=p, seed=seed)
        t_width = mfdfa_engine.cascade_theoretical_width(p=p)

        st.subheader("Nyers jel")
        st.caption("A generált nyers jel az idő függvényében.")
        mfdfa_engine.plot_signal_raw(measure, time)

if __name__ == "__main__":
    main()