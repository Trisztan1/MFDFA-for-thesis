import numpy as np
import streamlit as st
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

        n_levels, p, seed = pl.sg_binomial_cascade_parameters()

        step = pl.sidebar_step()

        # making the multifractal signal
        time, measure = mfdfa_engine.binomial_cascade(n_levels=n_levels, p=p, seed=seed)
        t_width = mfdfa_engine.cascade_theoretical_width(p=p)
        N = pl.sg_length_of_the_signal(time)
        lag_start, lag_stop, lag_num, q_start, q_stop, q_num, order = pl.sidebar_mfdfa_parameters(N)
        # gettind lag_mf, dfa_mf and q_list
        lag_mf, dfa_mf, q_list = mfdfa_engine.run_mfdfa(measure, lag_start=lag_start, lag_stop=lag_stop, lag_num=lag_num, q_start=q_start, q_stop=q_stop, q_num=q_num, order=order)
        fit_start, fit_end = pl.sidebar_fitting_rane_mf(lag_mf)
        pl.sidebar_displaying_time_series_length(N)

        q_show = mfdfa_engine.get_q_show()
        hq, r2 = mfdfa_engine.compute_hq(lag_mf=lag_mf, dfa_mf=dfa_mf, q_list=q_list, fit_start=fit_start, fit_end=fit_end) 
        tau, alpha, f_alpha = mfdfa_engine.spectrum(hq=hq, q_list=q_list)
        r_alpha_min, r_alpha_max, width_robust, r_alpha_peak, asymmetry_robust = mfdfa_engine.spectrum_width_robust(alpha=alpha, f_alpha=f_alpha, q_list=q_list, q_width_max=q_width_max, positive_q_only=positive_q_only, f_floor=0.0)
        alpha_min, alpha_max, width_raw, alpha_peak, asymmetry = mfdfa_engine.spectrum_stats(alpha=alpha, f_alpha=f_alpha)

        ### Plotting ####
        pl.raw_signal_plot(time, measure, step)
        pl.integrated_signal_plot(time, measure, step)
        pl.fluctuation_mfdfa_plot(q_list, lag_mf, dfa_mf, hq, r2, q_show, fit_start, fit_end)
        pl.gen_hurst_plot(q_list, hq)
        pl.mass_exponent_plot(q_list, tau)
        pl.singularity_spectrum_plot(alpha, f_alpha)
        pl.spectrum_statistics_plot(width_robust, width_raw, r_alpha_min, r_alpha_max, alpha_min, alpha_max, r_alpha_peak, alpha_peak, asymmetry_robust, asymmetry, r2, p)

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

                step = pl.sidebar_step()
                time_x, N = pl.getting_time(signal, sampling_rate)
                lag_start, lag_stop, lag_num, q_start, q_stop, q_num, order = pl.sidebar_mfdfa_parameters(N)
                lag_mf, dfa_mf, q_list = mfdfa_engine.run_mfdfa(signal, lag_start=lag_start, lag_stop=lag_stop, lag_num=lag_num, q_start=q_start, q_stop=q_stop, q_num=q_num, order=order)
                fit_start, fit_end = pl.sidebar_fitting_rane_mf(lag_mf)
                pl.sidebar_displaying_time_series_length(N)

                q_show = mfdfa_engine.get_q_show()
                hq, r2 = mfdfa_engine.compute_hq(lag_mf=lag_mf, dfa_mf=dfa_mf, q_list=q_list, fit_start=fit_start, fit_end=fit_end) 
                tau, alpha, f_alpha = mfdfa_engine.spectrum(hq=hq, q_list=q_list)
                r_alpha_min, r_alpha_max, width_robust, r_alpha_peak, asymmetry_robust = mfdfa_engine.spectrum_width_robust(alpha=alpha, f_alpha=f_alpha, q_list=q_list, q_width_max=q_width_max, positive_q_only=positive_q_only, f_floor=0.0)
                alpha_min, alpha_max, width_raw, alpha_peak, asymmetry = mfdfa_engine.spectrum_stats(alpha=alpha, f_alpha=f_alpha)

                # Plotting
                pl.raw_signal_plot(time_x, signal, step)
                pl.integrated_signal_plot(time_x, signal, step)
                pl.fluctuation_mfdfa_plot(q_list, lag_mf, dfa_mf, hq, r2, q_show, fit_start, fit_end)
                pl.gen_hurst_plot(q_list, hq)
                pl.mass_exponent_plot(q_list, tau)
                pl.singularity_spectrum_plot(alpha, f_alpha)
                pl.spectrum_statistics_plot(width_robust, width_raw, r_alpha_min, r_alpha_max, alpha_min, alpha_max, r_alpha_peak, alpha_peak, asymmetry_robust, asymmetry, r2)

        else:
            st.warning("Még nem töltöttél fel semmit.")



if __name__ == "__main__":
    main()

