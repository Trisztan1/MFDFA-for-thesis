import numpy as np
import streamlit as st
import mfdfa_engine
from utils import pages_logic as pl

def main():
    st.set_page_config(
        page_title="DFA",
        page_icon="📊",
        layout="wide"
    )

    st.title("It tudod megnézni az adatod ***Monofraktál*** jellegét")
    
    signal_generation = pl.sg_sidebar_signal_generation()
    
    if signal_generation:
        H_param, theta, sigma, t_final, delta_t, step = pl.sg_fou_parameters()
        time, y = mfdfa_engine.generate_fou(t_final, delta_t, theta, sigma, H_param)
        N = pl.sg_length_of_the_signal(time)
        lag_start, lag_stop, lag_num = pl.sidebar_dfa_parameters(N)
        lag_mf, dfa_mf, q_list = mfdfa_engine.run_mfdfa(y, lag_start=lag_start, lag_stop=lag_stop, lag_num=lag_num)
        # here we getting the dfa
        dfa = mfdfa_engine.get_dfa(dfa_mf=dfa_mf, q_list=q_list)     
        fit_start, fit_end = pl.sidebar_fitting_range(lag_mf)
        # here we get the slope, intercept and the Hurst exponent
        slope, intercept, H, r2 = mfdfa_engine.fit_dfa_exponent(lag_mf=lag_mf, dfa=dfa, fit_start=fit_start, fit_end=fit_end)
        
        pl.sidebar_displaying_time_series_length(N)
            
    
        # Ploting
        pl.raw_signal_plot(time, y, step)
        pl.integrated_signal_plot(time, y, step)
        pl.fluctuation_function_plot(dfa, lag_mf, slope, intercept, fit_start, fit_end, H, r2)
    

    else:
        # this section will run when the user uploaded data

        # here we are checking st.session_state for selected data
        pl.session_checks()
        data_df = pl.file_check()

        if data_df is not None:
            pl.sidebar_else()
            sampling_rate = pl.sidebar_sampling_rate()
            start_analysis = pl.analysis_button()
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
                    exception_name = type(e).__name__
                    st.error(f"**{exception_name}: Az adatok feldolgozása nem sikerült. Győződj meg arról, hogy a CSV-fájl kizárólag numerikus értékeket tartalmaz, és nincsenek benne hiányzó mezők.")
                    st.stop()

                step = pl.sidebar_step()
                time_x, N = pl.getting_time(signal, sampling_rate)

                lag_start, lag_stop, lag_num = pl.sidebar_dfa_parameters(N=N)

                lag_mf, dfa_mf, q_list = mfdfa_engine.run_mfdfa(signal, lag_start=lag_start, lag_stop=lag_stop, lag_num=lag_num)

                dfa = mfdfa_engine.get_dfa(dfa_mf=dfa_mf, q_list=q_list)

                fit_start, fit_end = pl.sidebar_fitting_range(lag_mf=lag_mf)

                pl.sidebar_displaying_time_series_length(N)

                # here we get the slope, intercept and the Hurst exponent
                slope, intercept, H, r2 = mfdfa_engine.fit_dfa_exponent(lag_mf=lag_mf, dfa=dfa, fit_start=fit_start, fit_end=fit_end, subtract_one=False)


                ## Plotting begins here
                # Plotting the raw signal
                pl.raw_signal_plot(time_x, signal, step)
                # Plotting the integrated cumsum signal
                pl.integrated_signal_plot(time_x, signal, step)
                # Plotting the fluctuation function
                pl.fluctuation_function_plot(dfa=dfa, lag_mf=lag_mf, slope=slope, intercept=intercept, fit_start=fit_start, fit_end=fit_end, H=H, r2=r2)

        else:
            st.warning("Még nem töltöttél fel semmit.")
        


if __name__ == "__main__":
    main()

    