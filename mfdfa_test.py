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

    # ---Fou--- #
    # The fractional Gaussian noise
    H = 0.7
    dB = (t_final ** H) * fgn(N = time.size, H = H)

    # Initialise the array y
    y = np.zeros([time.size])

    # Integrate the process
    for i in range(1, time.size):
        y[i] = y[i-1] - theta * y[i-1] * delta_t + sigma * dB[i]

    # ---cascade--- #
    # y = binomial_cascade(n_levels=16, p=0.25, seed=0)
    # time = np.arange(len(y))


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
    
    # width-reporting robustness knobs (used later, in spectrum_width)
    q_width_max = 4          # trim fragile extreme-q tips when reporting width
    positive_q_only = False  # True = width from q>0 only (strongest anti-spurious defense)

    # The order of the polynomial fitting
    order = 1

   
    # MFDFA part
    lag_mf, dfa_mf = MFDFA(y, lag=lag, q=q_list, order=order)
    # Dfa part
    # lag, dfa = MFDFA(y, lag=lag, q=q, order=order)
    i2 = int(np.argmin(np.abs(q_list - 2)))
    dfa = dfa_mf[:, i2]
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
    df_2 = pd.DataFrame({"lag": lag_mf, "dfa": dfa, "idx": np.arange(len(lag_mf))})
    fig_2 = px.scatter(df_2, x="lag", y="dfa", log_x=True, log_y=True, hover_data=["idx"], labels={"lag": "scale s", "dfa": "F(s)"})
    st.plotly_chart(fig_2, use_container_width=True)


    ### Getting the real slope and plotting the loglog plot dfa and lag values ###
    # You get the best fit with the linear regression and the slope of that will be the Hurst exponent

    # essential computation
    # old streamlit for initial DFA
    fit_start = 10
    slope, intercept = np.polyfit(np.log(lag_mf)[fit_start:], np.log(dfa)[fit_start:], 1)
    H = slope - 1

    # the data points
    df_3 = pd.DataFrame({"lag": lag_mf, "dfa": dfa})
    fig_3 = px.scatter(df_3, x="lag", y="dfa", log_x=True, log_y=True, labels={"lag": "scale s", "dfa": "F(s)"})

    # overlay the fitted line over the fitted band
    fit_x = lag_mf[fit_start:]
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
    # R^2 is the goodness of fit
    fit_start_mf = 10
    hq, r2 = [], []
    for i in range(len(q_list)):
        x = np.log(lag_mf)[fit_start_mf:]
        yv = np.log(dfa_mf[:, i])[fit_start_mf:]
        coeffs = np.polyfit(x, yv, 1)
        hq.append(coeffs[0])

        resid = yv - np.polyval(coeffs, x)
        r2.append(1 - np.var(resid) / np.var(yv)) # 1.0 = perfect straight line
    
    hq, r2 = np.array(hq), np.array(r2)
    st.write(f"min fit R² across q: {r2.min():.4f}")

    # visualizing it #

    df_hq = pd.DataFrame({"q": q_list, "hq": hq})
    fig_hq = px.scatter(df_hq, x="q", y="hq", labels={"q": "q", "hq": "h(q)"})
    fig_hq.update_yaxes(range=[0, 2])
    st.plotly_chart(fig_hq, use_container_width=True)

    ### Legendre transform: h(q) -> alpha, f(alpha) ###
    # tau(q) = q*h(q) - 1  (the "total"; -1 is the box-counting convention) #
    tau = q_list * hq - 1

    # visualising tau over q list
    df_tau = pd.DataFrame({"tau": tau, "q": q_list})
    fig_tau = px.scatter(df_tau, x="q", y="tau", labels={"q": "q", "tau": "tau"})
    st.plotly_chart(fig_tau, use_container_width=True)

    # alpha = d(tau)/dq  — slope of the tau curve at each q (numerical derivative)
    alpha = np.gradient(tau, q_list)
    f_alpha = q_list * alpha - tau

    # visualising the spectrum
    df_spec = pd.DataFrame({"alpha": alpha, "f_alpha": f_alpha})
    fig_spec = px.scatter(df_spec, x="alpha", y="f_alpha", labels={"alpha": "⍺", "f_alpha": "f(⍺)"})
    st.plotly_chart(fig_spec, use_container_width=True)
    
    ## getting spectrum values for statistics ##
    # spectrum width values
    alpha_min = alpha.min()
    alpha_max = alpha.max()
    width_raw = alpha_max - alpha_min

    # skewness values
    alpha_peak = alpha[np.argmax(f_alpha)] # the alpha at the top of the arch
    left_width = alpha_peak - alpha_min    
    right_width = alpha_max - alpha_peak
    asymmetry = right_width - left_width   # >0 rough-skewed, <0 smooth-skewed

    width, a_min, a_max = spectrum_width(alpha, f_alpha, q_list, q_width_max, positive_q_only)

    st.write(f"Δα (robust) = {width:.4f}   |   Δα (raw) = {width_raw:.4f}")
    st.write(f"spec_range (robust): {a_min:.4f}-{a_max:.4f}   |   spec_range (raw): {alpha_min:.4f}-{alpha_max:.4f}")
    st.write(f"α peak = {alpha_peak:.4f}   |   asymmetry = {asymmetry:.4f}")

    ## this is for only when the cascade part is uncommented
    ## this is the way to test the multifractal signal validation functions in this version of the code
    ## if you comment out the cascade part fou will run and you get a monofractal test signal
    # st.write(f"cascade_theoritical_width: {cascade_theoretical_width(p=0.25)}")





###### FUNCTIONS ######
### Spectrum width, robustly ###
def spectrum_width(alpha, f_alpha, q_list, q_width_max, positive_q_only, f_floor=0.0):
    keep = np.abs(q_list) <= q_width_max  # drop the fragile extreme-q tips
    if positive_q_only:
        keep &= (q_list > 0)
    
    keep &= (f_alpha >= f_floor)
    a = alpha[keep]

    if a.size == 0:
        return (np.nan, np.nan, np.nan)

    return (a.max() - a.min(), a.min(), a.max()) 


### Making a multifractal dummy signal for validation ###
def binomial_cascade(n_levels=10, p=0.4, seed=None):
    """
    Generate a 1D random binomial (multiplicative) cascade.
    Returns a multifractal measure of length 2**n_levels.
    """
    rng = np.random.default_rng(seed) # random number generator
    n = 2 ** n_levels
    measure = np.ones(n) # you will get an array containing 1 as much as your n

    for level in range(n_levels):
        block_size = 2 ** (n_levels - level)
        num_blocks = 2 ** level

        for i in range(num_blocks):
            start = i * block_size
            mid = start + block_size // 2
            end = start + block_size

            # random which half gets the larger share
            w1 = p if rng.random() > 0.5 else (1 - p)
            w2 = 1 - w1

            measure[start:mid] *= w1
            measure[mid:end] *= w2
        
    return measure

### Making a function to get the theoritical spectrum width for validation ###
def cascade_theoretical_width(p):
    a_min = -np.log2(max(p, 1 - p))
    a_max = -np.log2(min(p, 1 - p))

    return a_max - a_min
    






if __name__=="__main__":
    main()

