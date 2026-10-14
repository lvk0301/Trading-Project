"""Backtest of the user's FX:XAUUSD SMC rule set v0.1 (docs/SMC_XAUUSD_rules_v0.1.md).

Data comes from data/*.json (TradingView MCP get_ohlcv dumps, UTC timestamps = bar open).

Two modes:
  exact  - M15 setup + M5 entry/exit, as written in the rules (M5 history only ~1 month).
  proxy  - M15 used for both setup and the M5 steps (anchor, confirmation, SL, exit CHoCH),
           so the full 3 months can be tested. This is an approximation, not the rule set.

Everything is causal: a bar's information is used only after that bar has closed.
"""
import argparse
import bisect
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
VN = timezone(timedelta(hours=7))

TF_SEC = {"5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}


# --------------------------------------------------------------------------- data
@dataclass
class Bars:
    tf: str
    t: np.ndarray  # open time (unix sec, UTC)
    o: np.ndarray
    h: np.ndarray
    l: np.ndarray
    c: np.ndarray

    @property
    def n(self):
        return len(self.t)

    def close_time(self, i):
        return int(self.t[i]) + TF_SEC[self.tf]


def load(tf):
    d = json.load(open(DATA / f"xauusd_{tf}.json"))["bars"]
    a = {k: np.array(d[k], dtype=float) for k in "ohlc"}
    t = np.array(d["t"], dtype=np.int64)
    # the last bar is still forming when the data was pulled -> drop it
    return Bars(tf, t[:-1], a["o"][:-1], a["h"][:-1], a["l"][:-1], a["c"][:-1])


def atr(b: Bars, n):
    """Pine ta.atr (RMA of true range)."""
    tr = np.empty(b.n)
    tr[0] = b.h[0] - b.l[0]
    pc = b.c[:-1]
    tr[1:] = np.maximum(b.h[1:] - b.l[1:], np.maximum(abs(b.h[1:] - pc), abs(b.l[1:] - pc)))
    out = np.full(b.n, np.nan)
    if b.n < n:
        return out
    out[n - 1] = tr[:n].mean()
    for i in range(n, b.n):
        out[i] = (out[i - 1] * (n - 1) + tr[i]) / n
    return out


def load_news():
    ev = json.load(open(DATA / "us_calendar.json"))["result"]
    ts = sorted({int(datetime.fromisoformat(e["date"].replace("Z", "+00:00")).timestamp())
                 for e in ev if e.get("importance") == 1})
    return ts


# ------------------------------------------------------------- LuxAlgo structure
@dataclass
class Event:
    i: int            # bar index of the break (known at its close)
    bull: bool
    tag: str          # "CHoCH" / "BOS"
    level: float
    pivot_i: int
    ob_i: int
    ob_lo: float
    ob_hi: float


@dataclass
class Structure:
    events: list = field(default_factory=list)
    trend: np.ndarray = None          # bias after each bar: 1 bull, -1 bear, 0 none
    hi_level: np.ndarray = None       # current pivot-high level after each bar
    lo_level: np.ndarray = None
    pivots_hi: list = field(default_factory=list)  # (pivot_i, level, confirm_i)
    pivots_lo: list = field(default_factory=list)
    by_bar: dict = field(default_factory=dict)


def structure(b: Bars, size, swing: "Structure" = None):
    """Port of LuxAlgo Smart Money Concepts leg / pivot / BOS-CHoCH / order-block logic.

    size=5 with `swing` given -> internal structure (with the internal != swing level check).
    """
    n = b.n
    vol = atr(b, 200)
    hv = (b.h - b.l) >= 2 * np.nan_to_num(vol, nan=np.inf)
    ph = np.where(hv, b.l, b.h)   # parsed highs
    pl = np.where(hv, b.h, b.l)   # parsed lows

    s = Structure(trend=np.zeros(n, int), hi_level=np.full(n, np.nan), lo_level=np.full(n, np.nan))
    leg = 0
    hi = {"lvl": math.nan, "crossed": False, "i": -1}
    lo = {"lvl": math.nan, "crossed": False, "i": -1}
    bias = 0
    prev_hi, prev_lo = math.nan, math.nan
    for i in range(n):
        new_leg = leg
        if i >= size:
            if b.h[i - size] > b.h[i - size + 1:i + 1].max():
                new_leg = 0
            elif b.l[i - size] < b.l[i - size + 1:i + 1].min():
                new_leg = 1
        if new_leg != leg:
            p = i - size
            if new_leg == 1:      # start of bullish leg -> pivot low
                lo.update(lvl=b.l[p], crossed=False, i=p)
                s.pivots_lo.append((p, b.l[p], i))
            else:                 # start of bearish leg -> pivot high
                hi.update(lvl=b.h[p], crossed=False, i=p)
                s.pivots_hi.append((p, b.h[p], i))
            leg = new_leg

        extra_bull = extra_bear = True
        if swing is not None:
            extra_bull = hi["lvl"] != swing.hi_level[i]
            extra_bear = lo["lvl"] != swing.lo_level[i]

        if i > 0:
            if (not math.isnan(hi["lvl"]) and not hi["crossed"] and extra_bull
                    and b.c[i] > hi["lvl"] and not (b.c[i - 1] > prev_hi)):
                tag = "CHoCH" if bias == -1 else "BOS"
                hi["crossed"] = True
                bias = 1
                seg = pl[hi["i"]:i]
                k = hi["i"] + int(np.argmin(seg))
                e = Event(i, True, tag, hi["lvl"], hi["i"], k, min(pl[k], ph[k]), max(pl[k], ph[k]))
                s.events.append(e)
                s.by_bar[i] = e
            elif (not math.isnan(lo["lvl"]) and not lo["crossed"] and extra_bear
                    and b.c[i] < lo["lvl"] and not (b.c[i - 1] < prev_lo)):
                tag = "CHoCH" if bias == 1 else "BOS"
                lo["crossed"] = True
                bias = -1
                seg = ph[lo["i"]:i]
                k = lo["i"] + int(np.argmax(seg))
                e = Event(i, False, tag, lo["lvl"], lo["i"], k, min(pl[k], ph[k]), max(pl[k], ph[k]))
                s.events.append(e)
                s.by_bar[i] = e
        s.trend[i] = bias
        s.hi_level[i], s.lo_level[i] = hi["lvl"], lo["lvl"]
        prev_hi, prev_lo = hi["lvl"], lo["lvl"]
    return s


def internal_structure(b: Bars, swing_len=50):
    sw = structure(b, swing_len)
    return structure(b, 5, swing=sw), sw


# ------------------------------------------------------------------ HTF targets
@dataclass
class Target:
    kind: str        # "swing" / "OB" / "FVG"
    tf: str
    bull: bool       # True = bullish (below price, a sell target); False = bearish (above, buy target)
    lo: float
    hi: float
    t_created: int   # known from this time
    t_invalid: int   # invalid from this time (inf if never)


def luxalgo_fvgs(b: Bars):
    """LuxAlgo FVG with auto threshold, chart timeframe. Returns (i, bull, lo, hi)."""
    out = []
    bdp = np.zeros(b.n)
    bdp[1:] = (b.c[:-1] - b.o[:-1]) / (b.o[:-1] * 100)
    cum = np.cumsum(np.abs(bdp))
    for i in range(2, b.n):
        thr = cum[i] / i * 2
        if b.l[i] > b.h[i - 2] and b.c[i - 1] > b.h[i - 2] and bdp[i] > thr:
            out.append((i, True, b.h[i - 2], b.l[i]))
        elif b.h[i] < b.l[i - 2] and b.c[i - 1] < b.l[i - 2] and -bdp[i] > thr:
            out.append((i, False, b.h[i], b.l[i - 2]))
    return out


def build_targets(b: Bars, sw: Structure, h1: Bars):
    """Swing pivots (len 50), swing OBs and FVGs of one HTF with creation/invalidation times."""
    tg = []
    INF = 2 ** 62

    def first_close_beyond(i0, above, level):
        cc = b.c[i0 + 1:]
        idx = np.nonzero(cc > level)[0] if above else np.nonzero(cc < level)[0]
        return b.close_time(i0 + 1 + idx[0]) if len(idx) else INF

    h1_t = h1.t.tolist()

    def first_h1_beyond(t0, above, level):
        j0 = bisect.bisect_left(h1_t, t0)
        arr = h1.h[j0:] if above else h1.l[j0:]
        idx = np.nonzero(arr > level)[0] if above else np.nonzero(arr < level)[0]
        return h1.close_time(j0 + idx[0]) if len(idx) else INF

    for p, lvl, ci in sw.pivots_hi:
        tc = b.close_time(ci)
        tg.append(Target("swing", b.tf, False, lvl, lvl, tc, first_h1_beyond(int(b.t[p]) + TF_SEC[b.tf], True, lvl)))
    for p, lvl, ci in sw.pivots_lo:
        tc = b.close_time(ci)
        tg.append(Target("swing", b.tf, True, lvl, lvl, tc, first_h1_beyond(int(b.t[p]) + TF_SEC[b.tf], False, lvl)))
    for e in sw.events:
        # bullish break creates a bullish OB (below); invalid once an HTF candle closes below it
        if e.bull:
            tg.append(Target("OB", b.tf, True, e.ob_lo, e.ob_hi, b.close_time(e.i), first_close_beyond(e.i, False, e.ob_lo)))
        else:
            tg.append(Target("OB", b.tf, False, e.ob_lo, e.ob_hi, b.close_time(e.i), first_close_beyond(e.i, True, e.ob_hi)))
    for i, bull, lo, hi in luxalgo_fvgs(b):
        if bull:
            tg.append(Target("FVG", b.tf, True, lo, hi, b.close_time(i), first_close_beyond(i, False, lo)))
        else:
            tg.append(Target("FVG", b.tf, False, lo, hi, b.close_time(i), first_close_beyond(i, True, hi)))
    return tg


def targets_at(all_targets, T, entry, buy):
    """Targets valid at time T that lie fully beyond the entry in trade direction."""
    out = []
    for g in all_targets:
        if not (g.t_created <= T < g.t_invalid):
            continue
        if buy and not g.bull and g.lo > entry:
            out.append(g)
        elif not buy and g.bull and g.hi < entry:
            out.append(g)
    out.sort(key=lambda g: (g.lo - entry) if buy else (entry - g.hi))
    return out


# --------------------------------------------------------------------- backtest
@dataclass
class Params:
    mode: str = "exact"
    cost: float = 0.40            # round-trip spread+commission+slippage, $/oz
    rr_min: float = 1.5
    disp_body_atr: float = 1.0
    disp_close_frac: float = 0.25
    retest_frac: float = 0.30
    buffer_atr: float = 0.20
    news_before: int = 30 * 60
    news_after: int = 15 * 60


def fmt(ts):
    return datetime.fromtimestamp(ts, VN).strftime("%Y-%m-%d %H:%M")


def run(p: Params, start=None, end=None):
    m15 = load("15m")
    ltf = load("5m") if p.mode == "exact" else m15
    h1, h4, d1 = load("1h"), load("4h"), load("1d")
    news = load_news()

    m15_int, _ = internal_structure(m15)
    ltf_int, _ = internal_structure(ltf) if ltf is not m15 else (m15_int, None)
    atr15 = atr(m15, 14)
    atr_ltf = atr(ltf, 14)

    sw_h1, sw_h4, sw_d1 = structure(h1, 50), structure(h4, 50), structure(d1, 50)
    targets = build_targets(h1, sw_h1, h1) + build_targets(h4, sw_h4, h1)

    start = start or int(ltf.t[0])
    end = end or int(ltf.close_time(ltf.n - 1))

    d1_close = [d1.close_time(k) for k in range(d1.n)]
    h4_close = [h4.close_time(k) for k in range(h4.n)]

    def bias_at(sw, closes, T):
        j = bisect.bisect_right(closes, T) - 1
        return int(sw.trend[j]) if j >= 0 else 0

    def news_block(T):
        k = bisect.bisect_left(news, T - p.news_after)
        if k < len(news) and news[k] - p.news_before <= T:
            return news[k] + p.news_after
        return None

    # ---- M15 setups: CHoCH + displacement + FVG in the displacement leg
    funnel = {"choch": 0, "no_disp": 0, "no_fvg": 0, "setups": 0}
    setups = []
    for e in m15_int.events:
        if e.tag != "CHoCH" or m15.close_time(e.i) < start or m15.close_time(e.i) > end:
            continue
        if e.i < 250:
            continue
        funnel["choch"] += 1
        i = e.i
        body = abs(m15.c[i] - m15.o[i])
        rng = m15.h[i] - m15.l[i]
        frac = (m15.c[i] - m15.l[i]) / rng if rng > 0 else 0
        disp = body >= atr15[i - 1] and (frac >= 1 - p.disp_close_frac if e.bull else frac <= p.disp_close_frac)
        if not disp:
            funnel["no_disp"] += 1
            continue
        # FVGs whose middle candle lies in the leg (OB bar .. CHoCH bar); third candle <= CHoCH+1
        fvg = None
        for k in range(e.ob_i + 2, min(i + 1, m15.n - 1) + 1):
            if e.bull and m15.l[k] > m15.h[k - 2]:
                z = (m15.h[k - 2], m15.l[k])
            elif not e.bull and m15.h[k] < m15.l[k - 2]:
                z = (m15.h[k], m15.l[k - 2])
            else:
                continue
            wait_from = max(i, k)
            closes = m15.c[k + 1:wait_from + 1]
            broken = (closes < z[0]).any() if e.bull else (closes > z[1]).any()
            if not broken:
                fvg = (k, z, wait_from)
                break
        if fvg is None:
            funnel["no_fvg"] += 1
            continue
        k, z, wait_from = fvg
        funnel["setups"] += 1
        setups.append(dict(ev=e, fvg=z, fvg_i=k, ob=(e.ob_lo, e.ob_hi), active_from=m15.close_time(wait_from),
                           choch_time=m15.close_time(i)))

    # opposite CHoCH times (cancel signals), in order
    choch_times = [(m15.close_time(e.i), e.bull) for e in m15_int.events if e.tag == "CHoCH"]

    # ---- LTF simulation
    trades, log = [], []
    pos = None
    setup = None
    st_ptr = 0
    ltf_close = [ltf.close_time(k) for k in range(ltf.n)]
    ltf_events = ltf_int.by_bar
    i0 = bisect.bisect_left(ltf.t.tolist(), start)
    pending_entry = None
    pending_exit = None

    def note(s_, result, T):
        """One final log row per setup, with how far price got before the setup ended."""
        log.append(dict(choch=fmt(s_["choch_time"]), dir="BUY" if s_["ev"].bull else "SELL", result=result,
                         end=fmt(T), fvg=[round(x, 2) for x in s_["fvg"]], ob=[round(x, 2) for x in s_["ob"]],
                         zone_at_end=s_["zone"], pen_fvg=round(s_["pen"]["FVG"] * 100),
                         pen_ob=round(s_["pen"]["OB"] * 100), fvg_fail=s_["fvg_fail"], anchors=s_["anchors"],
                         events=list(s_["events"])))

    def cancel(reason, T):
        nonlocal setup
        if setup is not None:
            note(setup, reason, T)
        setup = None

    for j in range(i0, ltf.n):
        T_open = int(ltf.t[j])
        if T_open >= end:
            break

        # fills at the open of this bar
        if pending_exit is not None and pos is not None:
            px = ltf.o[j]
            _close_pos(pos, px, T_open, pending_exit, trades, p)
            pos = None
            pending_exit = None
        if pending_entry is not None:
            s_, sl, anchor_i, zone_kind = pending_entry
            pending_entry = None
            E = ltf.o[j]
            buy = s_["ev"].bull
            R = (E - sl) if buy else (sl - E)
            if R <= 0:
                note(s_, "gap past SL", T_open)
            else:
                tg = targets_at(targets, T_open, E, buy)
                if not tg:
                    note(s_, "no H1/H4 target", T_open)
                else:
                    near = tg[0]
                    dist = (near.lo - E) if buy else (E - near.hi)
                    rr = (dist - p.cost) / (R + p.cost)
                    if rr < p.rr_min:
                        note(s_, f"RR {rr:.2f} < {p.rr_min} (target {near.tf} {near.kind})", T_open)
                    else:
                        pos = dict(buy=buy, E=E, sl=sl, sl0=sl, R=R, t_in=T_open, targets=tg, armed=False,
                                   be=False, zone=zone_kind, rr_pot=rr, near=f"{near.tf} {near.kind}",
                                   choch=fmt(s_["choch_time"]),
                                   zoneLU=(round(s_["L"], 2), round(s_["U"], 2)), anchor=fmt(int(ltf.t[anchor_i])),
                                   fvg=tuple(round(x, 2) for x in s_["fvg"]), ob=tuple(round(x, 2) for x in s_["ob"]),
                                   d1=bias_at(sw_d1, d1_close, T_open), h4=bias_at(sw_h4, h4_close, T_open))
                        note(s_, "FILLED", T_open)

        # activate the next setup whose wait period has started
        while st_ptr < len(setups) and setups[st_ptr]["active_from"] <= T_open:
            if setup is not None:
                cancel("replaced by new CHoCH", T_open)
            s_ = setups[st_ptr]
            setup = dict(s_, zone="FVG", L=s_["fvg"][0], U=s_["fvg"][1], anchor=None, anchor_lo=None,
                         anchor_hi=None, blocked_until=None, start_j=j, pen={"FVG": 0.0, "OB": 0.0},
                         fvg_fail=None, anchors=0, events=[])
            st_ptr += 1

        # opposite M15 CHoCH known at this time cancels the setup
        if setup is not None:
            for tc, bull in choch_times:
                if setup["choch_time"] < tc <= T_open and bull != setup["ev"].bull:
                    cancel("opposite M15 CHoCH", tc)
                    break

        b_o, b_h, b_l, b_c = ltf.o[j], ltf.h[j], ltf.l[j], ltf.c[j]
        T_close = ltf_close[j]

        # ---- manage open position (intrabar SL first = conservative)
        if pos is not None:
            buy = pos["buy"]
            hit = (b_l <= pos["sl"]) if buy else (b_h >= pos["sl"])
            if hit:
                px = min(b_o, pos["sl"]) if buy else max(b_o, pos["sl"])
                _close_pos(pos, px, T_open, "BE" if pos["be"] else "SL", trades, p)
                pos = None
            else:
                if not pos["be"] and ((b_h >= pos["E"] + pos["R"]) if buy else (b_l <= pos["E"] - pos["R"])):
                    pos["be"] = True
                    pos["sl"] = pos["E"] + p.cost if buy else pos["E"] - p.cost
                if not pos["armed"]:
                    for g in pos["targets"]:
                        if (buy and b_h >= g.lo) or (not buy and b_l <= g.hi):
                            pos["armed"] = True
                            pos["touched"] = f"{g.tf} {g.kind}"
                            break
                ev = ltf_events.get(j)
                if pos["armed"] and ev is not None and ev.tag == "CHoCH" and ev.bull != buy:
                    pending_exit = "target+CHoCH"

        # ---- setup state machine on this LTF bar
        if setup is None:
            continue
        buy = setup["ev"].bull
        L, U = setup["L"], setup["U"]
        W = U - L
        pen = ((U - b_l) / W if buy else (b_h - L) / W) if W > 0 else (1.0 if (b_l <= U if buy else b_h >= L) else 0.0)
        setup["pen"][setup["zone"]] = max(setup["pen"][setup["zone"]], pen)
        # zone failure (close beyond the far side) has priority over entry
        if (b_c < L) if buy else (b_c > U):
            if setup["zone"] == "FVG":
                ob_lo, ob_hi = setup["ob"]
                setup.update(zone="OB", L=ob_lo, U=ob_hi, anchor=None, fvg_fail=fmt(T_open))
                setup["start_j"] = j + 1
                if (b_c < ob_lo) if buy else (b_c > ob_hi):
                    cancel("OB broken", T_open)
                continue
            cancel("OB broken", T_open)
            continue
        if j < setup["start_j"]:
            continue
        if setup["blocked_until"] is not None and T_open < setup["blocked_until"]:
            continue
        thr = U - p.retest_frac * W if buy else L + p.retest_frac * W
        if setup["anchor"] is None:
            touched = (b_l <= thr and b_h >= L) if buy else (b_h >= thr and b_l <= U)
            if touched:
                setup.update(anchor=j, anchor_lo=b_l, anchor_hi=b_h)
                setup["anchors"] += 1
            continue
        # confirmation: close beyond the anchor candle's extreme
        if (b_c > setup["anchor_hi"]) if buy else (b_c < setup["anchor_lo"]):
            a = setup["anchor"]
            buf = p.buffer_atr * atr_ltf[j]
            sl = ltf.l[a:j + 1].min() - buf if buy else ltf.h[a:j + 1].max() + buf
            blk = news_block(T_close)
            if pos is not None or pending_entry is not None:
                setup.update(anchor=None)
                setup["events"].append(f"{fmt(T_close)} signal skipped: already in a trade")
                continue
            if blk is not None:
                setup.update(anchor=None, blocked_until=blk)
                setup["events"].append(f"{fmt(T_close)} signal skipped: news window")
                continue
            pending_entry = (setup, sl, a, setup["zone"])
            setup = None   # one filled trade per CHoCH; a skipped entry also consumes it

    if setup is not None:
        note(setup, "still waiting at end of data", int(ltf.t[ltf.n - 1]))
    if pos is not None:
        _close_pos(pos, ltf.c[ltf.n - 1], int(ltf.t[ltf.n - 1]), "open at end", trades, p)
    return trades, log, funnel


def _close_pos(pos, px, T, reason, trades, p):
    pnl = (px - pos["E"]) if pos["buy"] else (pos["E"] - px)
    pnl -= p.cost
    trades.append(dict(
        dir="BUY" if pos["buy"] else "SELL", choch=pos["choch"], entry_time=fmt(pos["t_in"]), exit_time=fmt(T),
        entry=round(pos["E"], 2), sl=round(pos["sl0"], 2), exit=round(px, 2), risk=round(pos["R"], 2),
        R=round(pnl / pos["R"], 2), reason=reason, zone=pos["zone"], rr_pot=round(pos["rr_pot"], 2),
        zone_LU=pos["zoneLU"], fvg=pos["fvg"], ob=pos["ob"], anchor=pos["anchor"],
        nearest_target=pos["near"], touched=pos.get("touched", ""), be=pos["be"],
        with_d1=(pos["d1"] == (1 if pos["buy"] else -1)), d1=pos["d1"], h4=pos["h4"]))


def summarize(trades):
    if not trades:
        return dict(n=0)
    r = np.array([t["R"] for t in trades])
    eq = np.cumsum(r)
    dd = (np.maximum.accumulate(np.concatenate([[0], eq]))[1:] - eq).max()
    wins = r[r > 0]
    losses = r[r < 0]
    return dict(n=len(r), win_rate=round((r > 0).mean() * 100, 1), total_R=round(r.sum(), 2),
                avg_R=round(r.mean(), 3), avg_win=round(wins.mean(), 2) if len(wins) else 0,
                avg_loss=round(losses.mean(), 2) if len(losses) else 0,
                profit_factor=round(wins.sum() / -losses.sum(), 2) if len(losses) else float("inf"),
                max_dd_R=round(dd, 2))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="exact", choices=["exact", "proxy"])
    ap.add_argument("--cost", type=float, default=0.40)
    ap.add_argument("--start")
    ap.add_argument("--out")
    a = ap.parse_args()
    st = int(datetime.fromisoformat(a.start).replace(tzinfo=timezone.utc).timestamp()) if a.start else None
    tr, lg, fn = run(Params(mode=a.mode, cost=a.cost), start=st)
    if a.out:
        json.dump(dict(trades=tr, log=lg, funnel=fn, summary=summarize(tr)), open(a.out, "w"), indent=1,
                  ensure_ascii=False, default=float)
    print(json.dumps(fn))
    print(json.dumps(summarize(tr)))
    for t in tr:
        print(t)
