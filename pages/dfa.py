import numpy as np
import streamlit as st
import mfdfa_engine

def main():
    st.set_page_config(
        page_title="DFA",
        page_icon="📊",
        layout="wide"
    )

    st.title("It tudod megnézni az adatod ***Monofraktál*** jellegét")
    
    signal_generation = sg_sidebar_signal_generation()
    
    if signal_generation:
        H_param, theta, sigma, t_final, delta_t, step = sg_fou_parameters()

        time, y = mfdfa_engine.generate_fou(t_final, delta_t, theta, sigma, H_param)
        N = sg_length_of_the_signal(time)

        lag_start, lag_stop, lag_num = sidebar_dfa_parameters(N)

        lag_mf, dfa_mf, q_list = mfdfa_engine.run_mfdfa(y, lag_start=lag_start, lag_stop=lag_stop, lag_num=lag_num)

        # here we getting the dfa
        dfa = mfdfa_engine.get_dfa(dfa_mf=dfa_mf, q_list=q_list)
        
        fit_start, fit_end = sidebar_fitting_range(lag_mf)

        sidebar_displaying_time_series_length(N)

            
    
        
        raw_signal_plot(time, y, step)

        integrated_signal(time, y, step)

        # here we get the slope, intercept and the Hurst exponent
        slope, intercept, H, r2 = mfdfa_engine.fit_dfa_exponent(lag_mf=lag_mf, dfa=dfa, fit_start=fit_start, fit_end=fit_end)

        fluctuation_function_plot(dfa, lag_mf, slope, intercept, fit_start, fit_end, H, r2)
    

    else:
        # this section will run when the user uploaded data

        # here we are checking st.session_state for selected data
        session_checks()
        data_df = file_check()

        if data_df is not None:
            sidebar_else()
            sampling_rate = sidebar_sampling_rate()
            start_analysis = analysis_button()
            clear_analysis()

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
                    exception_name = type(e).__name__
                    st.error(f"**{exception_name}: Az adatok feldolgozása nem sikerült. Győződj meg arról, hogy a CSV-fájl kizárólag numerikus értékeket tartalmaz, és nincsenek benne hiányzó mezők.")
                    st.stop()

                step = sidebar_step()
                time_x, N = getting_time(signal, sampling_rate)

                lag_start, lag_stop, lag_num = sidebar_dfa_parameters(N=N)

                lag_mf, dfa_mf, q_list = mfdfa_engine.run_mfdfa(signal, lag_start=lag_start, lag_stop=lag_stop, lag_num=lag_num)

                dfa = mfdfa_engine.get_dfa(dfa_mf=dfa_mf, q_list=q_list)

                fit_start, fit_end = sidebar_fitting_range(lag_mf=lag_mf)

                sidebar_displaying_time_series_length(N)

                # here we get the slope, intercept and the Hurst exponent
                slope, intercept, H, r2 = mfdfa_engine.fit_dfa_exponent(lag_mf=lag_mf, dfa=dfa, fit_start=fit_start, fit_end=fit_end, subtract_one=False)


                ## Plotting begins here
                # Plotting the raw signal
                raw_signal_plot(time_x, signal, step)

                # Plotting the integrated cumsum signal
                integrated_signal(time_x, signal, step)

                # Plotting the fluctuation function
                fluctuation_function_plot(dfa=dfa, lag_mf=lag_mf, slope=slope, intercept=intercept, fit_start=fit_start, fit_end=fit_end, H=H, r2=r2)

                
            

                

        else:
            st.warning("Még nem töltöttél fel semmit.")
        




#########################
#### ---FUNCTIONS--- ####


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

def sg_length_of_the_signal(N):
    N = len(N)
    return np.array(N)






####### Using real data part ####### 
### Sidebar ###

def sidebar_else():
    with st.sidebar:
        st.info(f"Kiválasztott fájl: {st.session_state.selected_file}")

def analysis_button():
    # implementing an analysis button if it is true the dfa analysis of the data will begin
    with st.sidebar:
        start_analysis = st.button("Analízis megkezdése")
    
    if start_analysis:
        st.session_state.analysis_started = True
    
    return start_analysis

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


def sidebar_displaying_time_series_length(N):
    with st.sidebar:
        st.info(f"Az idősoros adat hossza: {N}")


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




### Other Functions ###

def clear_analysis():
    with st.sidebar:
        clear_analysis = st.button("Analízis törlése")

    if clear_analysis:
        st.session_state.analysis_started = False
        st.rerun()



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




def getting_time(signal, sampling_rate):
    dt = 1.0 / sampling_rate
    N = len(signal)

    time_x = np.arange(N) * dt

    return time_x, N


### Plotting Functions ###

def raw_signal_plot(x, y, step):
    st.subheader("Nyers jel")
    st.caption("A generált nyers jel az idő függvényében.")
    mfdfa_engine.plot_signal_raw(x, y, step)

def integrated_signal(x, y, step):
    st.subheader("Integrált jel")
    st.caption("A jel átlagközepezett kumulatív összege — ezen fut a DFA. Zaj-szerű jelből bolyongás-szerűt csinál.")
    mfdfa_engine.plot_signal_cum_sum(x, y, step)

def fluctuation_function_plot(dfa, lag_mf, slope, intercept, fit_start, fit_end, H, r2):
    st.subheader("Fluktuációs fügvény F(s)")
    st.caption("A fluktuáció nagysága a skála (s) függvényében, log-log skálán. Az egyenes meredeksége adja a skálázási kitevőt (a monofraktál Hurst-kitevőt).")

    mfdfa_engine.plot_fluctuation(lag=lag_mf, dfa=dfa, slope=slope, intercept=intercept, fit_start=fit_start, fit_end=fit_end)
    st.write(f"Hurst-kitevő (H) = {H:.3f}  |  R² = {r2:.4f}")
    st.caption("Az R² azt mutatja, mennyire illeszkednek a pontok az egyenesre. 1-hez közeli érték jó illesztést jelent; ha alacsony, szűkítsd az illesztési tartományt.")

if __name__ == "__main__":
    main()

    