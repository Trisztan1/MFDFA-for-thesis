from MFDFA import MFDFA
from MFDFA import fgn
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import mfdfa_engine
from utils import pages_logic as pl


def main():

    # width-reporting robustness knobs (used later, in spectrum_width)
    q_width_max = 4          # trim fragile extreme-q tips when reporting width
    positive_q_only = False  # True = width from q>0 only (strongest anti-spurious defense)

    st.set_page_config(
        page_title="MF-DFA",
        page_icon="📊",
        layout="wide"
    )

    st.title("It tudod megnézni az adatod ***Multifraktál*** jellegét")

    with st.sidebar:
        signal_generation = st.toggle("Generálj jelet")

    if signal_generation:

        n_levels, p, seed = sg_binomial_cascade_parameters()

        step = pl.sidebar_step()

        # making the multifractal signal
        time, measure = mfdfa_engine.binomial_cascade(n_levels=n_levels, p=p, seed=seed)
        t_width = mfdfa_engine.cascade_theoretical_width(p=p)
        N = sg_length_of_the_signal(time)

        lag_start, lag_stop, lag_num, q_start, q_stop, q_num, order = sg_mfdfa_parameters(N)
        
        # gettind lag_mf, dfa_mf and q_list
        lag_mf, dfa_mf, q_list = mfdfa_engine.run_mfdfa(measure, lag_start=lag_start, lag_stop=lag_stop, lag_num=lag_num, q_start=q_start, q_stop=q_stop, q_num=q_num, order=order)
        
        fit_start, fit_end = sg_fitting_range(lag_mf)

        sidebar_displaying_time_series_length(N)


        q_show = mfdfa_engine.get_q_show()

        hq, r2 = mfdfa_engine.compute_hq(lag_mf=lag_mf, dfa_mf=dfa_mf, q_list=q_list, fit_start=fit_start, fit_end=fit_end) 

        tau, alpha, f_alpha = mfdfa_engine.spectrum(hq=hq, q_list=q_list)

        r_alpha_min, r_alpha_max, width_robust, r_alpha_peak, asymmetry_robust = mfdfa_engine.spectrum_width_robust(alpha=alpha, f_alpha=f_alpha, q_list=q_list, q_width_max=q_width_max, positive_q_only=positive_q_only, f_floor=0.0)

        alpha_min, alpha_max, width_raw, alpha_peak, asymmetry = mfdfa_engine.spectrum_stats(alpha=alpha, f_alpha=f_alpha)



        ### Plotting ####
        raw_signal_plot(time, measure, step)
        integrated_signal_plot(time, measure, step)
        fluctuation_mfdfa_plot(q_list, lag_mf, dfa_mf, hq, r2, q_show, fit_start, fit_end)
        gen_hurst_plot(q_list, hq)
        mass_exponent_plot(q_list, tau)
        singularity_spectrum_plot(alpha, f_alpha)
        spectrum_statistics_plot(width_robust, width_raw, r_alpha_min, r_alpha_max, alpha_min, alpha_max, r_alpha_peak, alpha_peak, asymmetry_robust, asymmetry, r2, p)

    else:
        pl.session_checks()
        data_df = pl.file_check()
        if data_df is not None:
            pl.sidebar_else()
            sampling_rate = pl.sidebar_sampling_rate()
            pl.analysis_button()
            pl.clear_analysis()

            if st.session_state.analysis_started:
                start_analysis = True
            else:
                start_analysis = False

            if start_analysis:
                if data_df.shape[1] != 1:
                    st.error("Pontosan 1 oszlopot kell tartalmazzon a feldolgozott jel.")
                    st.stop()

                try:
                    signal = data_df.to_numpy().astype(float).ravel()
                    if not np.isfinite(signal).all():
                        st.error("Az jeledben nem lehetnek hiányzott értékek/kihagyott mezők és NaN értékek.")
                        st.stop()
                except ValueError as e:
                        exception_name = type(e).__name__ # to get only the name if .__name__ is not there you get the whole arror message
                        st.error(f"**{exception_name}: Az adatok feldolgozása nem sikerült. Győződj meg arról, hogy a CSV-fájl kizárólag numerikus értékeket tartalmaz, és nincsenek benne hiányzó mezők.")
                        st.stop()

            else:
                ...


        else:
            st.warning("Még nem töltöttél fel semmit.")



#########################
#### ---Functions--- ####

####### Generating signal part ####### 

# sg stands for signal generation part here

def sg_binomial_cascade_parameters():
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

    return n_levels, p, seed


def sg_mfdfa_parameters(N=None):
    with st.sidebar:
        st.markdown("___")
        st.subheader("MF-DFA Paraméterek")

        lag_start = st.number_input(
            "lag start (log10)", min_value=0.0, value=0.5, step=0.1, format="%.1f",
            help="A legkisebb skála, 10 hatványaként megadva (0.5 → 10^0.5 ≈ 3 minta). Ez a legkisebb ablakméret, amin a fluktuációt mérjük."
        )

        lag_stop = st.number_input(
            "lag end (log10)", min_value=lag_start+0.1, value=3.6, step=0.1, format="%.1f",
            help="A legnagyobb skála, 10 hatványaként megadva (3 → 10^3 = 1000 minta). Ne haladja meg a jel hosszának negyedét. Ha van törés a jelben, ezt érdemes bővíteni, hogy látszódjon."
        )

        st.info(f"Legnagyobb választott ablakméret: {round(10**lag_stop)}")
        
        if N:
            st.warning(f"Legnagyobb használható ablak: {N // 4}")

        lag_num = st.number_input(
            "number of lags", min_value=5, value=100, step=1,
            help="Hány skálát vizsgáljunk a start és stop között, logaritmikusan elosztva. Több pont = simább ábra, de a nagyon apró skálák egész számmá kerekítve összeolvadhatnak."
        )

        q_start = st.number_input(
            "q_start", min_value=-10.0, max_value=-0.5, value=-5.0, step=0.5, format="%.1f",
            help="A legkisebb (legnegatívabb) q érték. A negatív q-k a kis fluktuációkat emelik ki. Nagyon negatív értékek instabilak lehetnek — a spektrum bal széle innen származik."  
        )

        q_stop = st.number_input(
            "q_stop", min_value=0.5, max_value=10.0, value=5.0, step=0.5, format="%.1f",
            help="A legnagyobb (legpozitívabb) q érték. A pozitív q-k a nagy fluktuációkat emelik ki. A spektrum jobb széle innen származik."
        )

        with st.sidebar.expander("Advanced settings"):
            q_num = st.number_input(
            "number of q values", min_value=11, max_value=201, value=101, step=2,
            help="Hány q értéket vizsgáljunk a tartományban. Több érték = simább h(q) görbe és spektrum, de nem ad több információt, csak részletesebb megjelenítést."
        )

            order = st.number_input(
                "order", min_value=1, max_value=3, value=1, step=1,
                help="A szegmensenként kivont polinom fokszáma. 1 = lineáris trend (DFA1), 2 = másodfokú, 3 = harmadfokú. Magasabb fokszám több lassú trendet távolít el, de a kis skálákon túlillesztheti a fluktuációkat. Kezdd 1-gyel."
            )

    return lag_start, lag_stop, lag_num, q_start, q_stop, q_num, order

def sg_length_of_the_signal(N):
    N = len(N)
    return np.array(N)

def sg_fitting_range(lag_mf):
    with st.sidebar:
        st.markdown("___")
        st.subheader("Illesztési taromány")

        fit_start = st.slider(
            "fit start (index)", min_value=0, max_value=len(lag_mf)-5, value=0,
            help="Hol kezdődjön az illesztés. Hagyd ki az apró skálák zaját a bal oldalon."
        )

        fit_end = st.slider(
            "fit end (index)", min_value=fit_start+3, max_value=len(lag_mf) - 1, value=len(lag_mf) - 1,
            help="Hol végződjön az illesztés. A nagy skálák (jobb szél) is zajosak lehetnek."
        )

        st.caption(f"Fit tartomány: s = {lag_mf[fit_start]:,.0f} → {lag_mf[fit_end]:,.0f}")


    return fit_start, fit_end


## Displaying N

def sidebar_displaying_time_series_length(N):
    with st.sidebar:
        st.info(f"Az idősoros adat hossza: {N}")


#### Plotting Functions ####

def raw_signal_plot(x, y, step):
    st.subheader("Nyers jel")
    st.caption("A generált nyers jel az idő függvényében.")
    mfdfa_engine.plot_signal_raw(x, y, step)


def integrated_signal_plot(x, y, step):
    st.subheader("Integrált jel")
    st.caption("A jel átlagközepezett kumulatív összege — ezen fut a DFA. Zaj-szerű jelből bolyongás-szerűt csinál.")
    mfdfa_engine.plot_signal_cum_sum(x, y, step)

def fluctuation_mfdfa_plot(q_list, lag_mf, dfa_mf, hq, r2, q_show, fit_start, fit_end):
    st.subheader("Fluktuációs függvények (q szerint)")
    st.caption("Minden q-hoz egy fluktuációs görbe tartozik, log-log skálán. Ha a görbék párhuzamosak → monofraktál; ha szétnyílnak (különböző meredekségek) → multifraktál. A negatív q-görbék a legzajosabbak — ezekről olvasd le az illesztési tartományt.")
    mfdfa_engine.plot_fluctuation_mf(
        q_list=q_list, lag_mf=lag_mf, dfa_mf=dfa_mf, hq=hq, r2=r2, q_show=q_show,
        fit_start=fit_start, fit_end=fit_end,
    )

def gen_hurst_plot(q_list, hq):
    st.subheader("Generalizált Hurst-kitevők h(q)")
    st.caption("A skálázási kitevő q függvényében. Vízszintes vonal → monofraktál (egyetlen kitevő); lejtő → multifraktál (q-tól függő kitevők). Minél meredekebb a lejtés, annál erősebb a multifraktalitás.")
    mfdfa_engine.plot_hq(q_list=q_list, hq=hq)


def mass_exponent_plot(q_list, tau):
    st.subheader("Tömegkitevő τ(q)")
    st.caption("A tömegkitevő q függvényében, a h(q) átalakítása. Egyenes vonal → monofraktál; görbült vonal → multifraktál. A görbület adja a spektrum szélességét a Legendre-transzformáció után.")
    mfdfa_engine.plot_tau(q_list=q_list, tau=tau)

def singularity_spectrum_plot(alpha, f_alpha):
    st.subheader("Szingularitási spektrum f(α)")
    st.caption("A multifraktál spektrum — a végeredmény. Egyetlen pont → monofraktál; széles ív → multifraktál. Az ív szélessége (Δα) a multifraktalitás mértéke; a csúcs a leggyakoribb lokális kitevő.")
    mfdfa_engine.plot_spectrum(alpha=alpha, f_alpha=f_alpha)

def spectrum_statistics_plot(width_robust, width_raw, r_alpha_min, r_alpha_max, alpha_min, alpha_max, r_alpha_peak, alpha_peak, asymmetry_robust, asymmetry, r2, p):
    st.subheader("Spektrum statisztikák")
    st.caption("A spektrum számszerű jellemzői. Δα a szélesség (a multifraktalitás mértéke) — a robust verzió a megbízhatatlan szélső pontok levágásával számol. Az asymmetry az ív ferdesége (>0 a durva oldal felé, <0 a sima felé), az α peak a leggyakoribb lokális kitevő. Kaszkád esetén a theoretical Δα az ismert elméleti érték, az error pedig a visszanyerés pontossága.")
    mfdfa_engine.plot_spectrum_stats(r_width=width_robust, width_raw=width_raw, r_alpha_min=r_alpha_min, r_alpha_max=r_alpha_max, alpha_min=alpha_min, alpha_max=alpha_max, r_alpha_peak=r_alpha_peak, alpha_peak=alpha_peak, r_asymmetry=asymmetry_robust, asymmetry=asymmetry, r2=r2, p=p)

if __name__ == "__main__":
    main()

