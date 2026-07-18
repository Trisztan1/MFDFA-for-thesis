from MFDFA import MFDFA
from MFDFA import fgn
import numpy as np
import pandas as pd
import streamlit as st
# from streamlit.runtime.scriptrunner import get_script_run_ctx
import plotly.express as px

def main():
    #integration time and time sampling
    t_final = 2000
    delta_t = 0.001

    # some drift theta and diffusion sigma parameters
    theta = 0.3
    sigma = 0.1

    time = np.arange(0, t_final, delta_t)

    # The fractional Gaussian noise
    H = 0.7
    dB = (t_final ** H) * fgn(N = time.size, H = H)

    # Initialise the array y
    y = np.zeros([time.size])

    # Integrate the process
    for i in range(1, time.size):
        y[i] = y[i-1] - theta * y[i-1] * delta_t + sigma * dB[i]


    # Select a band of lags, which usually ranges from
    # very small segments of data, to very long ones, as
    lag = np.unique(np.logspace(0.5, 3, 100).astype(int))
    # Notice these must be ints, since these will segment
    # the data into chucks of lag size

    # Select power q
    q = 2

    # The order of the polynomial fitting
    order = 1

    # Obtain the (MF)DFA as:
    lag, dfa = MFDFA(y, lag=lag, q=q, order=order)

    # To uncover the Hurst index, lets get some log-log plots


    #### Multifractal part ####
    

    #### Streamlit ####

    ### First step getting the raw data ###
    step = 500
    df = pd.DataFrame({"time": time[::step], "y": y[::step]})
    fig = px.line(df, x="time", y="y")
    st.plotly_chart(fig, use_container_width=True)


    ### Calculating the mean centered cumulative sum ###

    y_cumsum = np.cumsum(y-y.mean())
    df_1 = pd.DataFrame({"time": time[::step], "y": y_cumsum[::step]})
    fig_1 = px.line(df_1, x="time", y="y")
    st.plotly_chart(fig_1, use_container_width=True)

    # st.write(lag)

    ### loglog plot the raw dfa and lag ###
    # so you can later choose the right slice [a:b] 
    # because the lower and the higher end values of the dfa can be misleading regarding getting the slope

    dfa = dfa.flatten()
    df_2 = pd.DataFrame({"lag": lag, "dfa": dfa, "idx": np.arange(len(lag))})
    fig_2 = px.scatter(df_2, x="lag", y="dfa", log_x=True, log_y=True, hover_data=["idx"], labels={"lag": "scale s", "dfa": "F(s)"})
    st.plotly_chart(fig_2, use_container_width=True)


    ### Getting the real slope and plotting the loglog plot dfa and lag values ###
    # You get the best fit with the linear regression and the slope of that will be the Hurst exponent

    # essential computation
    slope, intercept = np.polyfit(np.log(lag)[10:], np.log(dfa)[10:], 1)
    H = slope - 1

    # the data points
    df_3 = pd.DataFrame({"lag": lag, "dfa": dfa})
    fig_3 = px.scatter(df_3, x="lag", y="dfa", log_x=True, log_y=True, labels={"lag": "scale s", "dfa": "F(s)"})

    # overlay the fitted line over the fitted band
    fit_x = lag[10:]
    fit_y = np.exp(slope * np.log(fit_x) + intercept)
    fig_3.add_scatter(x=fit_x, y=fit_y, mode="lines", name=f"slope = {slope:.3f}")

    st.plotly_chart(fig_3, use_container_width=True)
    st.write(f"slope = {slope:.3f}  →  H ≈ {H:.3f}")


if __name__=="__main__":
    main()

