"""
Resource model for "The Internet of Agents: Resource Requirements and
Architectural Limits" (S. M. Alamouti and F. Arjomandi).

This script reproduces the numerical results of the paper from the stated
parameters:

  * Table 2  - uplink capacity, daily traffic, combined processing index, and
               daily energy for four adoption levels, relative to a reference
               workload.
  * Fig. 2   - required device share versus demand relative to shared capacity
               (Eq. 1, first line).
  * Fig. 3   - required device contribution for three shared-capacity cases.
  * Eq. 1    - reduction factor F of shared processing (third line) and the
               corresponding reduction in shared infrastructure.
  * Speech and vision examples - device busy time and energy.
  * Eq. 2 / Fig. 4 - device memory for monolithic agents and shared
               microservices.

Only the uplink capacity row of Table 2 uses Monte Carlo simulation. All other
results are direct calculations.

Usage:
    python ioa_resource_model.py                       # full report
    python ioa_resource_model.py --replications R --minutes N
        R independent replications of N simulated one-minute intervals each
        (default 10 x 40,000 = 400,000 intervals per workload); uplink
        multiples are reported with 95% confidence intervals.

Requires Python 3.9+ and NumPy.
"""

import argparse
import numpy as np

# ---------------------------------------------------------------------------
# Population and operating periods (assumptions)
# ---------------------------------------------------------------------------
PEOPLE = 10_000                # sample population; multiples are assumed to apply to the whole population
MACHINES = 1_000
PERSONAL_MINUTES = 16 * 60     # personal services operate 16 waking hours per day
MACHINE_HOURS = 8              # one eight-hour machine shift within personal hours
DAYS_PER_MONTH = 30            # decimal gigabytes are used throughout

# ---------------------------------------------------------------------------
# Data sizes and rates
# ---------------------------------------------------------------------------
IMAGE_MBIT = 1.4               # background or still image (derived from assumed compression of 1,440 x 1,920 images)
FRAME_MBIT = 0.28              # video frame (same derivation)
SPEECH_MBPS = 0.020            # compressed speech, 20 kbit/s (assumption)
TELEMETRY_MBPS = 0.010         # machine telemetry, 10 kbit/s (assumption)
REFERENCE_UPLINK_GB_MONTH = 2.0  # personal uplink per month (published measurement, Ericsson Mobility Report)
OTHER_TRAFFIC_BURST_MBPS = 1.0   # remaining personal traffic modeled as 1 Mbit/s bursts

# ---------------------------------------------------------------------------
# Processing (published measurements)
# ---------------------------------------------------------------------------
# Sustainable requests per second on one server configuration with prefix
# caching (Kim et al., arXiv:2506.04301).
RATE_CONVERSATION = 6.4        # single-interaction conversation (reference request)
RATE_QA = 2.6                  # multistep question answering
RATE_SHOPPING = 1.2            # shopping
# Agent tasks are assumed to be an equal mix of question answering and shopping.
AGENT_TASK_WEIGHT = 0.5 * (RATE_CONVERSATION / RATE_QA) + 0.5 * (RATE_CONVERSATION / RATE_SHOPPING)

# Speech recognition and synthesis on a PC-class CPU (Mazzone and Pau,
# Edge AI Audio Models Testbench): seconds of processing and joules of
# active-system energy per second of audio.
ASR_SECONDS_PER_AUDIO_SECOND = 0.064
TTS_SECONDS_PER_AUDIO_SECOND = 0.034
ASR_JOULES_PER_AUDIO_SECOND = 1.40
TTS_JOULES_PER_AUDIO_SECOND = 1.24

# Vision on a smartphone-class neural processing unit (Gherasim and Garcia
# Sanchez, arXiv:2511.13453): milliseconds per image.
NPU_MS_PER_IMAGE_MIN = 0.6     # compact image-classification model
NPU_MS_PER_IMAGE_MAX = 40.0    # largest object-detection models

# ---------------------------------------------------------------------------
# Workloads (Table 1). Reference = present use; four adoption levels = assumptions.
#   speech_in, speech_out : minutes per person per day
#   still_images          : individual still images per person per day
#   background_hours      : hours of background images per person per day
#   video_minutes         : minutes of active video per person per day
#   fps                   : personal and machine video frames per second
#   background_interval   : seconds between background images
#   camera_machine_share  : share of machines supplying camera data
#   cameras_per_machine   : cameras per participating machine
#   camera_hours          : camera operation per participating machine (hours per day)
#   tasks_person, tasks_machine : complete tasks per day
#   task_weight           : processing per task relative to a reference request
# ---------------------------------------------------------------------------
WORKLOADS = {
    "Reference":    dict(speech_in=5,   speech_out=2.5, still_images=20, background_hours=0, video_minutes=0,
                         fps=5,  background_interval=None, camera_machine_share=0.10, cameras_per_machine=1,
                         camera_hours=1 / 3, tasks_person=10,  tasks_machine=24,  task_weight=1.0),
    "Intermittent": dict(speech_in=30,  speech_out=15,  still_images=0,  background_hours=2, video_minutes=10,
                         fps=5,  background_interval=10, camera_machine_share=0.10, cameras_per_machine=1,
                         camera_hours=4,     tasks_person=20,  tasks_machine=48,  task_weight=AGENT_TASK_WEIGHT),
    "Regular":      dict(speech_in=60,  speech_out=30,  still_images=0,  background_hours=4, video_minutes=20,
                         fps=5,  background_interval=10, camera_machine_share=0.25, cameras_per_machine=1,
                         camera_hours=6,     tasks_person=40,  tasks_machine=96,  task_weight=AGENT_TASK_WEIGHT),
    "Extensive":    dict(speech_in=120, speech_out=60,  still_images=0,  background_hours=8, video_minutes=40,
                         fps=5,  background_interval=10, camera_machine_share=0.50, cameras_per_machine=1,
                         camera_hours=8,     tasks_person=80,  tasks_machine=192, task_weight=AGENT_TASK_WEIGHT),
    "Intensive":    dict(speech_in=120, speech_out=60,  still_images=0,  background_hours=8, video_minutes=40,
                         fps=10, background_interval=5,  camera_machine_share=0.50, cameras_per_machine=3,
                         camera_hours=8,     tasks_person=160, tasks_machine=384, task_weight=AGENT_TASK_WEIGHT),
}
LEVELS = ["Intermittent", "Regular", "Extensive", "Intensive"]

# Processing-share sets (visual, speech, task) used to combine the three stages.
PROCESSING_SHARES = [(1 / 3, 1 / 3, 1 / 3), (0.6, 0.2, 0.2), (0.2, 0.6, 0.2), (0.2, 0.2, 0.6)]
# Share of reference energy used by processing; the rest is split equally
# between transport and fixed consumption.
PROCESSING_ENERGY_SHARES = np.linspace(0.50, 0.95, 10)

# Capacity rule: 99th percentile of one-minute demand during overlapping hours.
CAPACITY_PERCENTILE = 99.0


def other_personal_traffic_mbit_per_day(ref):
    """Reference daily uplink less reference speech and still images (Mbit per person per day)."""
    total = REFERENCE_UPLINK_GB_MONTH * 8_000 / DAYS_PER_MONTH
    return total - ref["speech_in"] * 60 * SPEECH_MBPS - ref["still_images"] * IMAGE_MBIT


def uplink_capacity_mbps(w, rng, minutes, media_scale=1.0):
    """Monte Carlo estimate of the required uplink capacity (Mbit/s) for workload w.

    Each simulated minute draws, independently:
      * people speaking (binomial), people in background-image or active-video
        mode (multinomial, modes do not overlap), people sending other traffic
        as 1 Mbit/s bursts (binomial), and still images (binomial events);
      * camera-equipped machines with cameras on (binomial); all cameras on a
        machine operate together.
    Machine telemetry is constant. The required capacity is the chosen
    percentile of one-minute mean demand.
    """
    ref = WORKLOADS["Reference"]
    p_speech = w["speech_in"] / PERSONAL_MINUTES
    p_background = w["background_hours"] * 60 / PERSONAL_MINUTES
    p_video = w["video_minutes"] / PERSONAL_MINUTES
    p_other = other_personal_traffic_mbit_per_day(ref) / (60 * OTHER_TRAFFIC_BURST_MBPS * PERSONAL_MINUTES)

    background_rate = (IMAGE_MBIT / w["background_interval"] if w["background_interval"] else 0.0) * media_scale
    video_rate = w["fps"] * FRAME_MBIT * media_scale
    camera_machines = round(w["camera_machine_share"] * MACHINES)
    machine_camera_rate = w["cameras_per_machine"] * w["fps"] * FRAME_MBIT * media_scale

    speaking = rng.binomial(PEOPLE, p_speech, minutes)
    visual = rng.multinomial(PEOPLE, [p_background, p_video, 1 - p_background - p_video], minutes)
    other = rng.binomial(PEOPLE, p_other, minutes)
    stills = rng.binomial(PEOPLE * w["still_images"], 1 / PERSONAL_MINUTES, minutes) if w["still_images"] else 0
    cameras_on = rng.binomial(camera_machines, w["camera_hours"] / MACHINE_HOURS, minutes)

    demand = (speaking * SPEECH_MBPS
              + visual[:, 0] * background_rate
              + visual[:, 1] * video_rate
              + other * OTHER_TRAFFIC_BURST_MBPS
              + stills * IMAGE_MBIT * media_scale / 60
              + MACHINES * TELEMETRY_MBPS
              + cameras_on * machine_camera_rate)
    return np.percentile(demand, CAPACITY_PERCENTILE)


def daily_totals(w):
    """Daily frames, speech processing time and energy, weighted tasks, and access traffic (Mbit)."""
    ref = WORKLOADS["Reference"]
    camera_machines = round(w["camera_machine_share"] * MACHINES)
    background_frames = w["background_hours"] * 3600 / w["background_interval"] if w["background_interval"] else 0
    person_frames = w["still_images"] + background_frames + w["video_minutes"] * 60 * w["fps"]
    machine_frames = camera_machines * w["cameras_per_machine"] * w["camera_hours"] * 3600 * w["fps"]

    speech_seconds_in = PEOPLE * w["speech_in"] * 60
    speech_seconds_out = PEOPLE * w["speech_out"] * 60

    person_uplink = (w["speech_in"] * 60 * SPEECH_MBPS
                     + w["still_images"] * IMAGE_MBIT
                     + background_frames * IMAGE_MBIT
                     + w["video_minutes"] * 60 * w["fps"] * FRAME_MBIT
                     + other_personal_traffic_mbit_per_day(ref))
    machine_uplink = (MACHINES * MACHINE_HOURS * 3600 * TELEMETRY_MBPS
                      + machine_frames * FRAME_MBIT)
    downlink = PEOPLE * w["speech_out"] * 60 * SPEECH_MBPS   # synthesized speech

    return dict(
        frames=PEOPLE * person_frames + machine_frames,
        speech_time=speech_seconds_in * ASR_SECONDS_PER_AUDIO_SECOND + speech_seconds_out * TTS_SECONDS_PER_AUDIO_SECOND,
        speech_energy=speech_seconds_in * ASR_JOULES_PER_AUDIO_SECOND + speech_seconds_out * TTS_JOULES_PER_AUDIO_SECOND,
        tasks=w["task_weight"] * (PEOPLE * w["tasks_person"] + MACHINES * w["tasks_machine"]),
        traffic=PEOPLE * person_uplink + machine_uplink + downlink,
    )


def uplink_multiples_with_ci(seed, replications, minutes, media_scale=1.0):
    """Uplink multiples relative to the reference, with 95% confidence intervals.

    Each replication uses an independent random stream. The confidence
    interval of the mean is the mean plus or minus t * s / sqrt(R), where s is
    the standard deviation across replications and t the 97.5% Student-t
    quantile for R - 1 degrees of freedom.
    """
    from statistics import mean, stdev
    t_975 = {2: 12.71, 3: 4.30, 4: 3.18, 5: 2.78, 6: 2.57, 7: 2.45, 8: 2.36, 9: 2.31, 10: 2.26,
             15: 2.14, 20: 2.09, 30: 2.05}
    t = t_975.get(replications, 1.96)
    streams = np.random.default_rng(seed).spawn(replications)
    samples = {level: [] for level in LEVELS}
    for rng in streams:
        ref = uplink_capacity_mbps(WORKLOADS["Reference"], rng, minutes)  # reference keeps present image sizes
        for level in LEVELS:
            samples[level].append(uplink_capacity_mbps(WORKLOADS[level], rng, minutes, media_scale) / ref)
    out = {}
    for level, values in samples.items():
        m = mean(values)
        half = t * stdev(values) / np.sqrt(replications) if replications > 1 else float("nan")
        out[level] = (m, half)
    return out


def table2(seed, replications, minutes):
    """Rows of Table 2 for each adoption level, relative to the reference workload."""
    ref = daily_totals(WORKLOADS["Reference"])
    uplink = uplink_multiples_with_ci(seed, replications, minutes)
    rows = {}
    for level in LEVELS:
        d = daily_totals(WORKLOADS[level])
        stage = dict(visual=d["frames"] / ref["frames"],
                     speech=d["speech_time"] / ref["speech_time"],
                     task=d["tasks"] / ref["tasks"])
        speech_energy = d["speech_energy"] / ref["speech_energy"]
        traffic = d["traffic"] / ref["traffic"]
        processing = [a * stage["visual"] + b * stage["speech"] + c * stage["task"] for a, b, c in PROCESSING_SHARES]
        energy = []
        for p in PROCESSING_ENERGY_SHARES:
            for a, b, c in PROCESSING_SHARES:
                processing_energy = a * stage["visual"] + b * speech_energy + c * stage["task"]
                energy.append(p * processing_energy + (1 - p) / 2 * traffic + (1 - p) / 2 * 1.0)
        rows[level] = dict(
            uplink=uplink[level],
            traffic=traffic,
            processing=(min(processing), max(processing)),
            energy=(min(energy), max(energy)),
            stage=stage,
        )
    return rows


def required_device_share(demand_to_capacity, r=0.0):
    """Eq. 1, first line: u_min = max(0, (1 - C/D) / (1 - r))."""
    return max(0.0, (1 - 1 / demand_to_capacity) / (1 - r))


def reduction_factor(q, r):
    """Eq. 1, third line: F = 1 / (1 - q (1 - r))."""
    return 1 / (1 - q * (1 - r))


def memory_gb(installed, active, beta, b=0.25, p=0.02, o_m=0.025, o_s=0.025):
    """Eq. 2: memory of monolithic agents (all resident) and of shared microservices."""
    monolithic = installed * (b + o_m) + active * p
    microservices = beta * b + active * ((1 - beta) * b + p) + o_s
    return monolithic, microservices


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--replications", type=int, default=10, help="independent simulation replications")
    parser.add_argument("--minutes", type=int, default=40_000, help="simulated one-minute intervals per replication")
    parser.add_argument("--seed", type=int, default=1, help="random seed")
    args = parser.parse_args()

    print(f"Agent task weight (equal mix): {AGENT_TASK_WEIGHT:.2f} times a reference request\n")

    total = args.replications * args.minutes
    rows = table2(args.seed, args.replications, args.minutes)
    print(f"Table 2: requirements relative to the reference workload ({total:,} simulated minutes per workload)")
    print(f"{'Level':13s}{'Busy-hour uplink (95% CI)':>28s}{'Traffic':>9s}{'Processing':>16s}{'Energy':>16s}")
    for level, r in rows.items():
        m, half = r["uplink"]
        print(f"{level:13s}{m:12.2f} +/- {half:.3f} ({100 * half / m:.2f}%){r['traffic']:9.1f}"
              f"{r['processing'][0]:8.0f}-{r['processing'][1]:<7.0f}{r['energy'][0]:8.0f}-{r['energy'][1]:<7.0f}")
    reg = rows["Regular"]["stage"]
    print(f"\nRegular level by stage: visual {reg['visual']:.0f}x, task {reg['task']:.1f}x, speech {reg['speech']:.1f}x")
    lo, hi = rows["Regular"]["processing"]
    print(f"Regular combined index after fourfold efficiency gain: {lo / 4:.1f} to {hi / 4:.1f}")
    halved = uplink_multiples_with_ci(args.seed + 1, args.replications, args.minutes, media_scale=0.5)["Intensive"]
    print(f"Intensive uplink with half the image sizes: {halved[0]:.1f} +/- {halved[1]:.2f}")

    print("\nFig. 3: required device share (%), lower and upper estimates, r = 0")
    for capacity in (5, 10, 20):
        cells = []
        for level in LEVELS:
            lo, hi = rows[level]["processing"]
            cells.append(f"{level} {100 * required_device_share(lo / capacity):.0f}-{100 * required_device_share(hi / capacity):.0f}")
        print(f"  shared capacity {capacity:2d}x: " + ", ".join(cells))
    print("  demand relative to 20x capacity: " + ", ".join(
        f"{level} {rows[level]['processing'][0] / 20:.1f}-{rows[level]['processing'][1] / 20:.1f}" for level in LEVELS))

    print("\nEq. 1: reduction factor F and avoided shared infrastructure")
    for q in (0.90, 0.95):
        for r in (0.2, 0.0):
            f = reduction_factor(q, r)
            print(f"  q = {q:.2f}, r = {r:.1f}: F = {f:5.1f}, avoided = {100 * (1 - 1 / f):.0f}%")

    print("\nSpeech example (one person's device, 16-hour operating period)")
    for level in ("Regular", "Intensive"):
        w = WORKLOADS[level]
        busy = w["speech_in"] * 60 * ASR_SECONDS_PER_AUDIO_SECOND + w["speech_out"] * 60 * TTS_SECONDS_PER_AUDIO_SECOND
        energy_wh = (w["speech_in"] * 60 * ASR_JOULES_PER_AUDIO_SECOND + w["speech_out"] * 60 * TTS_JOULES_PER_AUDIO_SECOND) / 3600
        print(f"  {level}: busy {busy / 60:.1f} min/day ({100 * busy / (PERSONAL_MINUTES * 60):.2f}% of period), energy {energy_wh:.1f} Wh/day")

    print("\nVision example (regular level)")
    w = WORKLOADS["Regular"]
    person_frames = w["background_hours"] * 3600 / w["background_interval"] + w["video_minutes"] * 60 * w["fps"]
    machine_frames = w["camera_hours"] * 3600 * w["fps"] * w["cameras_per_machine"]
    for name, frames, period_s in (("person", person_frames, PERSONAL_MINUTES * 60), ("machine", machine_frames, MACHINE_HOURS * 3600)):
        lo = 100 * frames * NPU_MS_PER_IMAGE_MIN / 1000 / period_s
        hi = 100 * frames * NPU_MS_PER_IMAGE_MAX / 1000 / period_s
        print(f"  {name}: {frames:,.0f} frames/day, busy {lo:.2f}% to {hi:.1f}% of operating time")
    wi = WORKLOADS["Intensive"]
    load = wi["cameras_per_machine"] * wi["fps"] * NPU_MS_PER_IMAGE_MAX / 1000
    print(f"  intensive machine, largest models: {load:.1f} s of processing per second")

    print("\nEq. 2 / Fig. 4: device memory (GB), 10% of installed agents active, at least one")
    for installed in (5, 10, 20):
        active = max(1, round(0.1 * installed))
        mono, micro_distinct = memory_gb(installed, active, beta=0.0)
        _, micro_shared = memory_gb(installed, active, beta=0.9)
        print(f"  {installed:2d} installed, {active} active: monolithic {mono:.2f}, "
              f"microservices {micro_shared:.2f}-{micro_distinct:.2f}, ratio {mono / micro_distinct:.0f}-{mono / micro_shared:.0f}")


if __name__ == "__main__":
    main()
