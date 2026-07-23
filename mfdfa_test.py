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

    # here we use a list of q values instead of a single q
    # for multifractal analysus the MF part of the DFA
    q_list = np.linspace(-5, 5, 101)
    # q_list = np.linspace(-5, 5, 11)
    # we make this q list values by omitting 0 or values near zero if we might have a very samll decimal value instead of zero
    q_list = q_list[(q_list < -0.1) | (q_list > 0.1)]
    # q_list = q_list[q_list != 0]

    # The order of the polynomial fitting
    order = 1

    # Obtain the (MF)DFA as:
    # Dfa part
    lag, dfa = MFDFA(y, lag=lag, q=q, order=order)
    # MFDFA part
    lag_mf, dfa_mf = MFDFA(y, lag=lag, q=q_list, order=order)
    assert dfa_mf.shape[1] == len(q_list), f"{len(q_list)} q values but {dfa_mf.shape[1]} columns"

    # To uncover the Hurst index, lets get some log-log plots


    
    #### Streamlit ####

    ### Monofractal part ###
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

    st.write(f"dfa shape: {dfa.shape}")

    ### loglog plot the raw dfa and lag ###
    # so you can later choose the right slice [a:b] 
    # because the lower and the higher end values of the dfa can be misleading regarding getting the slope

    # old streamlit for initial DFA
    dfa = dfa.flatten()
    df_2 = pd.DataFrame({"lag": lag, "dfa": dfa, "idx": np.arange(len(lag))})
    fig_2 = px.scatter(df_2, x="lag", y="dfa", log_x=True, log_y=True, hover_data=["idx"], labels={"lag": "scale s", "dfa": "F(s)"})
    st.plotly_chart(fig_2, use_container_width=True)


    ### Getting the real slope and plotting the loglog plot dfa and lag values ###
    # You get the best fit with the linear regression and the slope of that will be the Hurst exponent

    # essential computation
    # old streamlit for initial DFA
    slice = 10
    slope, intercept = np.polyfit(np.log(lag)[slice:], np.log(dfa)[slice:], 1)
    H = slope - 1

    # the data points
    df_3 = pd.DataFrame({"lag": lag, "dfa": dfa})
    fig_3 = px.scatter(df_3, x="lag", y="dfa", log_x=True, log_y=True, labels={"lag": "scale s", "dfa": "F(s)"})

    # overlay the fitted line over the fitted band
    fit_x = lag[slice:]
    fit_y = np.exp(slope * np.log(fit_x) + intercept)
    fig_3.add_scatter(x=fit_x, y=fit_y, mode="lines", name=f"slope = {slope:.3f}")

    st.plotly_chart(fig_3, use_container_width=True)
    st.write(f"slope = {slope:.3f}  →  H ≈ {H:.3f}")

    ###########################
    #### Multifractal part ####
    st.write("# Multifractal Part")
    st.write()

    ## Multi-q fluctuation function bundle (diagnostic) ##
    # Purpose: choose the scaling range [a:b] used to fit h(q).
    # Each q weights different fluctuation magnitudes, so MFDFA returns one
    # F(s) curve per q (a column of dfa_mf). Plotting a few representative q's
    # on log-log axes shows where ALL curves scale cleanly (straight and
    # parallel) versus where they break down.
    # The bad scales are shared across q (too few samples per segment at small
    # lags, too few segments at large lags), so ONE slice serves every column.
    # Negative q's are the fragile ones and collapse first at small lags —
    # they set where the slice must start, not the well-behaved positive q's.
    # Only a handful of q's are drawn; all of them are still computed.
    q_show = [-5, -2, -1, 1, 2, 5]

    fig_mf = px.scatter(log_x=True, log_y=True, labels={"x": "scale s", "y": f"F(s)"})

    for qv in q_show:
        i = int(np.argmin(np.abs(q_list - qv)))
        fig_mf.add_scatter(x=lag_mf, y=dfa_mf[:, i], mode="markers", name=f"q= {q_list[i]:.1f}")

    st.plotly_chart(fig_mf, use_container_width=True)

    ### Generalised Hurst exponents h(q) ###
    # Fit one slope per q-column, all using the SAME slice chosen above.
    slice_mf = 10
    hq = []
    for i in range(len(q_list)):
        slope_mf = np.polyfit(np.log(lag_mf)[slice_mf:], np.log(dfa_mf[:, i])[slice_mf:], 1)[0]
        hq.append(slope_mf)
    
    hq = np.array(hq)

    # visualizing it #

    df_hq = pd.DataFrame({"q": q_list, "hq": hq})
    st.write(hq)
    fig_hq = px.scatter(df_hq, x="q", y="hq", labels={"q": "q", "hq": "h(q)"})
    fig_hq.update_yaxes(range=[0, 2])
    st.plotly_chart(fig_hq, use_container_width=True)
    st.write(dfa_mf.shape[1])
    st.write(len(q_list))





if __name__=="__main__":
    main()

