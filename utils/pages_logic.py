import streamlit as st
import numpy as np
import mfdfa_engine

def main():
    ...
########################################
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

def sidebar_displaying_time_series_length(N):
    with st.sidebar:
        st.info(f"Az idősoros adat hossza: {N}")

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

##################################

def getting_time(signal, sampling_rate):
    dt = 1.0 / sampling_rate
    N = len(signal)

    time_x = np.arange(N) * dt

    return time_x, N

def sg_length_of_the_signal(N):
    N = len(N)
    return np.array(N)


### Plotting Functions

#### Plotting Functions ####

def raw_signal_plot(x, y, step):
    st.subheader("Nyers jel")
    st.caption("A generált nyers jel az idő függvényében.")
    mfdfa_engine.plot_signal_raw(x, y, step)


def integrated_signal_plot(x, y, step):
    st.subheader("Integrált jel")
    st.caption("A jel átlagközepezett kumulatív összege — ezen fut a DFA. Zaj-szerű jelből bolyongás-szerűt csinál.")
    mfdfa_engine.plot_signal_cum_sum(x, y, step)


##############################
##### ---DFA Functions--- #####

####### Generating signal part ####### 

# sg stands for signal generation part here
def sg_sidebar_signal_generation():
    with st.sidebar:
        signal_generation = st.toggle("Generálj jelet")

    return signal_generation

def sg_fou_parameters():
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

            delta_t = st.number_input("delta_t", min_value=0.0001, value=0.01, format="%.4f",
            help="A lépésköz (mintavételezés). Kisebb érték finomabb felbontást és pontosabb integrálást ad.")

            step = st.number_input(
                "step",
                min_value=1,
                max_value=10000,
                step=1,
                value=1,
                help="Az ábra ritkítása: minden N. pontot mutatja. Nagyobb N = kevésbé részletes, de gyorsabb ábra. A DFA számítás mindig a teljes jelet használja."
            )

    return H, theta, sigma, t_final, delta_t, step

####### Shared functions #######

def sidebar_dfa_parameters(N = None):
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
        st.info(f"Legnagyobb választott ablakméret: {round(10**lag_stop)}")

        if N:
            st.warning(f"Legnagyobb használható ablak: {N // 4}")

        lag_num = st.number_input(
            "number of lags", min_value=5, value=100, step=1,
            help="Hány skálát vizsgáljunk a start és stop között, logaritmikusan elosztva. Több pont = simább ábra, de a nagyon apró skálák egész számmá kerekítve összeolvadhatnak."
        )

    return lag_start, lag_stop, lag_num

def sidebar_fitting_range(lag_mf):
    with st.sidebar:
        st.markdown("___")
        st.subheader("Illesztési taromány")

        fit_start = st.slider(
            "fit start (index)", min_value=0, max_value=max(0, len(lag_mf)-5), value=0,
            help="Hol kezdődjön az illesztés. Hagyd ki az apró skálák zaját a bal oldalon."
        )

        fit_end = st.slider(
            "fit end (index)", min_value=fit_start+3, max_value=len(lag_mf) - 1, value=len(lag_mf) - 1,
            help="Hol végződjön az illesztés. A nagy skálák (jobb szél) is zajosak lehetnek."
        )

        st.caption(f"Fit tartomány: s = {lag_mf[fit_start]:,.0f} → {lag_mf[fit_end]:,.0f}")

    return fit_start, fit_end

#### Plotting Functions #####

def fluctuation_function_plot(dfa, lag_mf, slope, intercept, fit_start, fit_end, H, r2):
    st.subheader("Fluktuációs fügvény F(s)")
    st.caption("A fluktuáció nagysága a skála (s) függvényében, log-log skálán. Az egyenes meredeksége adja a skálázási kitevőt (a monofraktál Hurst-kitevőt).")

    mfdfa_engine.plot_fluctuation(lag=lag_mf, dfa=dfa, slope=slope, intercept=intercept, fit_start=fit_start, fit_end=fit_end)
    st.write(f"Hurst-kitevő (H) = {H:.3f}  |  R² = {r2:.4f}")
    st.caption("Az R² azt mutatja, mennyire illeszkednek a pontok az egyenesre. 1-hez közeli érték jó illesztést jelent; ha alacsony, szűkítsd az illesztési tartományt.")



##############################
##### ---MF Functions--- #####

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

####### Shared functions #######

def sidebar_mfdfa_parameters(N=None):
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

def sidebar_fitting_rane_mf(lag_mf):
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

def sidebar_getting_p():
    with st.sidebar:
        p = st.slider(
            "p (split fraction)", min_value=0.01, max_value=0.99, value=0.25,
            help="A tömeg megosztási aránya minden osztásnál. p=0.5 → egyenletes (monofraktál). Minél távolabb 0.5-től, annál szélesebb a multifraktál spektrum."
        )

    return p


 #### Ploting Functions ####

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

def spectrum_statistics_plot(width_robust, width_raw, r_alpha_min, r_alpha_max, alpha_min, alpha_max, r_alpha_peak, alpha_peak, asymmetry_robust, asymmetry, r2, p = None):
    st.subheader("Spektrum statisztikák")
    st.caption("A spektrum számszerű jellemzői. Δα a szélesség (a multifraktalitás mértéke) — a robust verzió a megbízhatatlan szélső pontok levágásával számol. Az asymmetry az ív ferdesége (>0 a durva oldal felé, <0 a sima felé), az α peak a leggyakoribb lokális kitevő. Kaszkád esetén a theoretical Δα az ismert elméleti érték, az error pedig a visszanyerés pontossága.")
    mfdfa_engine.plot_spectrum_stats(r_width=width_robust, width_raw=width_raw, r_alpha_min=r_alpha_min, r_alpha_max=r_alpha_max, alpha_min=alpha_min, alpha_max=alpha_max, r_alpha_peak=r_alpha_peak, alpha_peak=alpha_peak, r_asymmetry=asymmetry_robust, asymmetry=asymmetry, r2=r2, p=p)



if __name__ == "__main__":
    main()