from MFDFA import MFDFA
from MFDFA import fgn
import numpy as np
import pandas as pd
import streamlit as st
# from streamlit.runtime.scriptrunner import get_script_run_ctx
import plotly.express as px


######### -----FUNCTIONS----- #########

###### ---COMPUTE LAYER--- ###### 
# fractional Ornstein-Uhlenbeck (fOU) this will generate the monofractal signal
# the signal has mean reversion and long term memory
def generate_fou(t_final=2000, delta_t=0.001, theta=0.3, sigma=0.1, H=0.7):
    time = np.arange(0, t_final, delta_t)
    dB = (t_final ** H) * fgn(N = time.size, H = H)
    y = np.zeros([time.size])
    # Integrate the process
    for i in range(1, time.size):
        y[i] = y[i-1] - theta * y[i-1] * delta_t + sigma * dB[i]

    return (time, y)

### Making a multifractal dummy signal for validation ###
def binomial_cascade(n_levels=10, p=0.4, seed=None):
    """
    Generate a 1D random binomial (multiplicative) cascade.
    Returns a multifractal measure of length 2**n_levels.
    """
    # this is for generating multifractal signal
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
    time = np.arange(len(measure))
    
    # here time is x and measure will be y which you feed into mfdfa 
    return (time, measure)

### Making a function to get the theoritical spectrum width for validation ###
def cascade_theoretical_width(p):
    a_min = -np.log2(max(p, 1 - p))
    a_max = -np.log2(min(p, 1 - p))

    return a_max - a_min


def run_mfdfa(y, lag_start=0.5, lag_stop=3, lag_num=100, q_start=-5, q_stop=5, q_num=101, order=1):
    # Select a band of lags, which usually ranges from
    # very small segments of data, to very long ones, as
    lag = np.unique(np.logspace(lag_start, lag_stop, lag_num).astype(int))
    # Notice these must be ints, since these will segment
    # the data into chucks of lag size

    # here we use a list of q values instead of a single q
    # for multifractal analysus the MF part of the DFA
    q_list = np.linspace(q_start, q_stop, q_num)
    # we make this q list values by omitting 0 or values near zero if we might have a very samll decimal value instead of zero
    q_list = q_list[(q_list < -0.1) | (q_list > 0.1)]

    # MFDFA part
    lag_mf, dfa_mf = MFDFA(y, lag=lag, q=q_list, order=order)

    return (lag_mf, dfa_mf, q_list)

def get_dfa(dfa_mf, q_list):
    # Dfa part
    # you get dfa which is created with a single q=2 instead of q_list
    # here i2 is the index number of q=2 so you can slice with it and get dfa with q=2
    i2 = int(np.argmin(np.abs(q_list - 2)))
    assert dfa_mf.shape[1] == len(q_list), f"{len(q_list)} q values but {dfa_mf.shape[1]} columns"
    dfa = dfa_mf[:, i2]

    return dfa

def fit_dfa_exponent(lag_mf, dfa, fit_start: int = None, fit_end: int = None, subtract_one=True):
    x = np.log(lag_mf)[fit_start:fit_end]
    yv = np.log(dfa)[fit_start:fit_end]

    coeffs= np.polyfit(x, yv, 1)
    slope = coeffs[0]
    intercept = coeffs[1]
    H = slope - 1 if subtract_one else slope

    resid = yv - np.polyval(coeffs, x)
    r2 = 1 - np.var(resid)/np.var(yv) if np.var(yv) > 0 else np.nan # 1.0 = perfect straight line

    return (slope, intercept, H, r2)

def get_q_show(values=(-5, -2, -1, 1, 2, 5)):
    return np.array(values)


def compute_hq(lag_mf, dfa_mf, q_list, fit_start: int = None, fit_end: int = None):
    hq, r2 = [], []
    for i in range(len(q_list)):
        x = np.log(lag_mf)[fit_start:fit_end]
        yv = np.log(dfa_mf[:, i])[fit_start:fit_end]
        coeffs = np.polyfit(x, yv, 1)
        hq.append(coeffs[0])

        resid = yv - np.polyval(coeffs, x)
        r2.append(1 - np.var(resid) / np.var(yv)) # 1.0 = perfect straight line
    
    hq, r2 = np.array(hq), np.array(r2)

    return (hq, r2)

def spectrum(hq, q_list):
    ### Legendre transform: h(q) -> alpha, f(alpha) ###
    # tau(q) = q*h(q) - 1  (the "total"; -1 is the box-counting convention) #
    tau = q_list * hq - 1

    # alpha = d(tau)/dq  — slope of the tau curve at each q (numerical derivative)
    alpha = np.gradient(tau, q_list)
    f_alpha = q_list * alpha - tau

    return (tau, alpha, f_alpha)


### Spectrum width, robustly ###
def spectrum_width_robust(alpha, f_alpha, q_list, q_width_max, positive_q_only, f_floor=0.0):
    # getting a more robust spectrum width
    keep = np.abs(q_list) <= q_width_max  # drop the fragile extreme-q tips
    if positive_q_only:
        keep &= (q_list > 0)
    
    keep &= (f_alpha >= f_floor)
    a = alpha[keep]
    f = f_alpha[keep]

    if a.size == 0:
        return (np.nan, np.nan, np.nan, np.nan)
    
    r_alpha_min = a.min()
    r_alpha_max = a.max()
    width_robust = a.max() - a.min()

    # skewness values
    r_alpha_peak = a[np.argmax(f)] # the alpha at the top of the arch
    left_width = r_alpha_peak - r_alpha_min    
    right_width = r_alpha_max - r_alpha_peak
    asymmetry_robust = right_width - left_width

    return (r_alpha_min, r_alpha_max, width_robust, r_alpha_peak, asymmetry_robust) 
    

def spectrum_stats(alpha, f_alpha):
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

    return (alpha_min, alpha_max, width_raw, alpha_peak, asymmetry)

###### ---PRESENTATION LAYER--- ######

### ---Monofractal Part--- ###
def plot_signal_raw(time, y, step=500):
    # First step getting the raw data
    df = pd.DataFrame({"time": time[::step], "y": y[::step]})
    fig = px.line(df, x="time", y="y")
    st.plotly_chart(fig, use_container_width=True)

def plot_signal_cum_sum(y, time, step=500):
    # Plot the cumsum of the raw signal
    y_cumsum = np.cumsum(y-y.mean())
    df = pd.DataFrame({"time": time[::step], "y": y_cumsum[::step]})
    fig = px.line(df, x="time", y="y")
    st.plotly_chart(fig, use_container_width=True)

def plot_fluctuation(lag, dfa, slope, intercept, fit_start: int = None, fit_end: int = None):
    # Plot the F(s) over s to get the slope dfa or h(2)
    # the data points
    df = pd.DataFrame({"lag": lag, "dfa": dfa})
    fig = px.scatter(df, x="lag", y="dfa", log_x=True, log_y=True, labels={"lag": "scale s", "dfa": "F(s)"})

    # overlay the fitted line over the fitted band
    fit_x = lag[fit_start:fit_end]
    fit_y = np.exp(slope * np.log(fit_x) + intercept)
    fig.add_scatter(x=fit_x, y=fit_y, mode="lines", name=f"slope = {slope:.3f}")

    st.plotly_chart(fig, use_container_width=True)

### ---Multifractal Part--- ###

def plot_fluctuation_mf(q_list, lag_mf, dfa_mf, hq, r2, q_show, fit_start: int = None, fit_end: int = None):

    # Plot multiple fluctuation functions weighted differently by q over s

    fig_mf = px.scatter(log_x=True, log_y=True, labels={"x": "scale s", "y": f"F(s)"})
    colors = px.colors.qualitative.Plotly

    for j, qv in enumerate(q_show):
        i = int(np.argmin(np.abs(q_list - qv)))
        color = colors[j % len(colors)]
        fig_mf.add_scatter(
            x=lag_mf, y=dfa_mf[:, i], mode="markers",
            marker=dict(color=color), name=f"q = {q_list[i]:.1f}  (h = {hq[i]:.3f})",
        )

        if fit_start is not None and fit_end is not None:
            fit_x = lag_mf[fit_start:fit_end]
            x = np.log(fit_x)
            yv = np.log(dfa_mf[fit_start:fit_end, i])
            intercept = np.polyfit(x, yv, 1)[1]
            fit_y = np.exp(hq[i] * np.log(fit_x) + intercept)
            fig_mf.add_scatter(
                x=fit_x, y=fit_y, mode="lines",
                line=dict(color=color), showlegend=False,
            )

    if fit_start is not None and fit_end is not None:
        fig_mf.add_vrect(
            x0=lag_mf[fit_start], x1=lag_mf[min(fit_end, len(lag_mf) - 1)],
            fillcolor="gray", opacity=0.15, line_width=0,
        )

    st.plotly_chart(fig_mf, use_container_width=True)

    st.write(f"min fit R² across q: {r2.min():.4f}")

def plot_hq(q_list, hq):
    # Plot the hq values over q
    df_hq = pd.DataFrame({"q": q_list, "hq": hq})
    fig_hq = px.scatter(df_hq, x="q", y="hq", labels={"q": "q", "hq": "h(q)"})
    fig_hq.update_yaxes(range=[0, 2])
    st.plotly_chart(fig_hq, use_container_width=True)

def plot_tau(q_list, tau):
    # Plotting tau over q
    df_tau = pd.DataFrame({"tau": tau, "q": q_list})
    fig_tau = px.scatter(df_tau, x="q", y="tau", labels={"q": "q", "tau": "tau"})
    st.plotly_chart(fig_tau, use_container_width=True)

def plot_spectrum(alpha, f_alpha):
    # Plotting the spectrum finally
    df_spec = pd.DataFrame({"alpha": alpha, "f_alpha": f_alpha})
    fig_spec = px.scatter(df_spec, x="alpha", y="f_alpha", labels={"alpha": "⍺", "f_alpha": "f(⍺)"})
    st.plotly_chart(fig_spec, use_container_width=True)

def plot_spectrum_stats(r_width, width_raw, r_alpha_min, r_alpha_max, alpha_min, alpha_max, r_alpha_peak, alpha_peak, r_asymmetry, asymmetry, r2, p: float = None):
    st.write(f"Δα (robust) = {r_width:.4f}   |   Δα (raw) = {width_raw:.4f}")
    st.write(f"spec_range (robust): {r_alpha_min:.4f}-{r_alpha_max:.4f}   |   spec_range (raw): {alpha_min:.4f}-{alpha_max:.4f}")
    st.write(f"α peak (raw) = {alpha_peak:.4f}   |   asymmetry (raw) = {asymmetry:.4f}")
    st.write(f"α peak (robust) = {r_alpha_peak:.4f}   |   asymmetry (robust) = {r_asymmetry:.4f}")
    st.write(f"min fit R² across q: {r2.min():.4f}")

    if p is not None:
        theo = cascade_theoretical_width(p)
        err_robust = abs(r_width - theo) / theo * 100
        err_raw = abs(width_raw - theo) / theo * 100
        st.write(f"theoretical Δα: {theo:.4f}  |  error (robust): {err_robust:.1f}%  |  error (raw): {err_raw:.1f}%")


