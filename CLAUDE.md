# Trading-Project

The user trades gold (XAUUSD), forex, VN stocks and crypto using Smart Money Concepts (SMC), and is still learning. They usually write in Vietnamese; reply in Vietnamese.

## SMC checklist
When the user asks about "checklist", "check list", the analysis steps, or whether to enter a trade, read `docs/smc-checklist.md` and explain it from that file: go through the 10 steps and the 8-question pre-trade checklist, using live chart data or the user's screenshot as the example when available. Keep the core rule: one "no" means no trade. The user tends to FOMO into trades when flat, so check premium/discount and POI location before any entry suggestion.

## TradingView
`.mcp.json` configures the TradingView MCP server (`mcp-tradingview`). The user may also have it as a claude.ai custom connector. It provides watchlists, OHLCV, technicals, alerts and the economic calendar, but not chart drawings; ask for a screenshot to see the user's drawn levels.
