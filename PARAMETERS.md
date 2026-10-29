# Model parameters

Parameters used in "The Internet of Agents: Resource Requirements and Architectural Limits." Each value is marked as a published measurement, a derived value, or an assumption.

## Population and operating periods

| Parameter | Value | Basis |
| --- | --- | --- |
| Sample population | 10,000 people, 1,000 machines | Assumption; multiples are assumed to apply to the whole population |
| Personal operating period | 16 hours per day | Assumption |
| Machine operating period | One 8-hour shift within personal hours | Assumption |
| Month | 30 days, decimal gigabytes | Convention |

## Data sizes and rates

| Parameter | Value | Basis |
| --- | --- | --- |
| Personal uplink, reference | 2 GB per month | Published measurement (Ericsson Mobility Report) |
| Background or still image | 1.4 Mbit | Derived from assumed compression of 1,440 x 1,920 images |
| Video frame | 0.28 Mbit | Derived from assumed compression of 1,440 x 1,920 images |
| Compressed speech | 20 kbit/s | Assumption |
| Machine telemetry | 10 kbit/s during operating hours | Assumption |
| Other personal traffic | Reference uplink less reference speech and still images, sent as 1 Mbit/s bursts, same at every level | Assumption |

## Processing and energy

| Parameter | Value | Basis |
| --- | --- | --- |
| Server throughput, single-interaction conversation | 6.4 requests/s | Published measurement (Kim et al.) |
| Server throughput, multistep question answering | 2.6 requests/s | Published measurement (Kim et al.) |
| Server throughput, shopping | 1.2 requests/s | Published measurement (Kim et al.) |
| Reference request | Single-interaction conversation | Assumption |
| Agent task | Equal mix of question answering and shopping, 3.9 times a reference request | Assumption; weight derived from the measurements |
| Speech recognition | 0.064 s and 1.40 J per second of audio | Published measurement (Mazzone and Pau) |
| Speech synthesis | 0.034 s and 1.24 J per second of audio | Published measurement (Mazzone and Pau) |
| Reply length | Half the length of input speech | Assumption |
| Vision on a smartphone NPU | 0.6 ms (compact classification) to 40 ms (largest detection) per image | Published measurement (Gherasim and Garcia Sanchez) |

## Workloads (Table 1)

| Setting | Reference | Intermittent | Regular | Extensive | Intensive |
| --- | --- | --- | --- | --- | --- |
| Speech input per person (minutes) | 5 | 30 | 60 | 120 | 120 |
| Synthesized speech per person (minutes) | 2.5 | 15 | 30 | 60 | 60 |
| Individual still images per person | 20 | 0 | 0 | 0 | 0 |
| Background images per person (hours) | 0 | 2 | 4 | 8 | 8 |
| Active video per person (minutes) | 0 | 10 | 20 | 40 | 40 |
| Video frames per second | 5 | 5 | 5 | 5 | 10 |
| Background image interval (seconds) | none | 10 | 10 | 10 | 5 |
| Machines supplying camera data | 10% | 10% | 25% | 50% | 50% |
| Cameras per participating machine | 1 | 1 | 1 | 1 | 3 |
| Camera operation per machine (hours) | 1/3 | 4 | 6 | 8 | 8 |
| Complete tasks per person | 10 | 20 | 40 | 80 | 160 |
| Complete tasks per machine | 24 | 48 | 96 | 192 | 384 |

The reference workload represents present use. The four adoption levels are assumptions.

## Methods

| Item | Value | Basis |
| --- | --- | --- |
| Busy-hour dimensioning | 99th percentile of one-minute uplink demand during overlapping operating hours (grade of service: exceeded in no more than 1% of intervals) | Method; estimated by Monte Carlo simulation, 400,000 intervals per workload, about +/-0.1% at 95% confidence |
| Arrivals | Independent; tasks as Poisson arrivals; camera and speech services on or off with probability set by daily duration; all cameras on a machine operate together | Assumption |
| Processing shares for combining stages (visual, speech, task) | Equal shares, and 60% to one stage with 20% to each other | Assumption |
| Processing share of reference energy | 50% to 95%; rest split equally between transport and fixed consumption | Assumption |
| Shared-capacity cases | 5, 10, and 20 times the reference daily processing | Assumption |
| Share of work eligible for devices, q | 0.90 and 0.95 | Assumption |
| Remaining shared work per unit assigned to devices, r | 0 to 0.2 | Assumption |

## Device memory (Eq. 2)

| Parameter | Value | Basis |
| --- | --- | --- |
| Installed agents | 5, 10, 20; 10% active, at least one | Assumption |
| Model and software memory per agent, b | 0.25 GB | Assumption (for example, a 270-million-parameter model at 4-bit to 8-bit precision) |
| Shareable fraction, beta | 0 (distinct models) to 0.9 (adapters on a shared base model) | Assumption |
| Private working memory per active agent, p | 0.02 GB | Assumption |
| Runtime memory per monolithic agent, o_m | 0.025 GB | Assumption |
| Shared runtime memory, o_s | 0.025 GB | Assumption |
