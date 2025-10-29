# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.18.1
#   kernelspec:
#     display_name: .venv
#     language: python
#     name: python3
# ---

# %%
from pathlib import Path
import openlifu_verification
import numpy as np
import matplotlib.pyplot as plt
datapath = Path(openlifu_verification.__file__).parent.parent.resolve() / "scripts" / "data"


# %%
data = np.load(datapath / "scan_freq_data.npz")


# %%
plt.plot(data['freq'], np.max(data['outputs'], axis=1),'.-')
plt.xlabel('Frequency (kHz)')
plt.ylabel('Peak (mV)')

# %%
plt.imshow(data['outputs'], aspect='auto', interpolation="None")

# %%
plt.plot(data['voltages'][1:], np.diff(np.max(data['outputs'], axis=1))/np.diff(data['voltages']),'.-')
plt.xlabel('Voltage (V)')
plt.ylabel('Peak (mV/V)')
