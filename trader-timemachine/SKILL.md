---
name: trader-timemachine
description: >-
  Indian Equities Time Machine. Replays a planned trade 10,000 times using Monte Carlo simulation
  drawn from the stock's own historical 5-minute bars in IST at that exact time of day, plus every past
  session the setup fired. Computes objective win/loss odds in INR.
argument-hint: "run [--replays 10000] [--write] | chart"
---

# trader-timemachine (NSE / BSE)

Simulates session paths before you risk capital.

```bash
python trader-timemachine/timemachine.py run                        # Replays trader/plan.json 10,000 times
python trader-timemachine/timemachine.py run --write                # Saves to trader/timemachine.json
python trader-timemachine/timemachine.py chart                      # Renders ASCII distribution fan chart
```

## Simulation Rules
- Stop-loss is strictly evaluated before profit target within any candle that touches both (conservative simulation).
- Replays evaluate terminal probabilities: target hit first %, stop hit first %, or open at 15:15 IST %.
