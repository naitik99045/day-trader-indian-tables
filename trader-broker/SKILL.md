---
name: trader-broker
description: >-
  Human-in-the-Loop Execution Coordinator for Indian Brokers. Prepares plain-English tickets,
  verifies risk approvals, and routes orders to the built-in Indian Paper Broker or formats payloads
  for DhanHQ and Zerodha Kite Connect.
argument-hint: "show | approve --index N --reply 'yes' | fill | log"
---

# trader-broker (NSE / BSE)

Coordinates order approvals and broker execution. No order is ever placed without explicit human confirmation.

```bash
python trader-broker/ticket.py show                                 # Review tickets and broker payloads
python trader-broker/ticket.py approve --index 1 --reply "yes"      # Confirm order #1
python trader-broker/ticket.py fill --symbol RELIANCE.NS --side buy --qty 15 --price 2950.00
python trader-broker/ticket.py log                                  # View execution history
```

## Supported Indian Brokers
- **Paper Broker (Default)**: Standalone simulated broker with realistic fill slippage and statutory charge accounting in INR.
- **DhanHQ API**: Standardized JSON payload generator for Dhan trading accounts.
- **Zerodha Kite Connect**: Formatted payloads for Kite API orders.
