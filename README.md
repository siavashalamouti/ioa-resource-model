# Internet of Agents resource model

Code and parameters for "The Internet of Agents: Resource Requirements and Architectural Limits" (S. M. Alamouti and F. Arjomandi).

## Contents

- `ioa_resource_model.py`: reproduces the numerical results of the paper.
- `PARAMETERS.md`: every model parameter, with its value and basis (published measurement, derived value, or assumption).

## Running

Requires Python 3.9 or later and NumPy.

```
pip install numpy
python ioa_resource_model.py
```

Options:

- `--replications R`: number of independent simulation replications (default 10).
- `--minutes N`: simulated one-minute intervals per replication (default 40,000), for 400,000 intervals per workload in total.
- `--seed S`: random seed (default 1).

The uplink multiples are reported with 95% confidence intervals computed across the replications. With the defaults, each multiple is estimated within about +/-0.1%.

## What the script reports

| Output | Paper item | Method |
| --- | --- | --- |
| Busy-hour uplink capacity relative to the reference, with 95% confidence intervals | Table 2, first row | Monte Carlo simulation, 99th percentile of one-minute demand |
| Daily traffic, processing index, and energy | Table 2, other rows | Direct calculation |
| Growth by processing stage | Text | Direct calculation |
| Effect of halved image sizes and fourfold efficiency | Text | Simulation and direct calculation |
| Required device share | Fig. 2 and Fig. 3 | Eq. 1, first line |
| Reduction factor F and avoided shared infrastructure | Text, abstract, and conclusion | Eq. 1, third line |
| Speech and vision device busy time | Text | Direct calculation from published measurements |
| Device memory | Eq. 2 and Fig. 4 | Direct calculation |

The paper rounds these values to show scale.
