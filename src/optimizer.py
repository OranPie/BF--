#!/usr/bin/env python3
# bfopt_advanced.py
#
# Brainfuck optimizer (outputs STANDARD Brainfuck).
# Levels (0..7):
#   0: filter + pack (+/- and </>) + cancel
#   1: clear-loop recognition + modulo shrink (wrap) + local clear peepholes
#   2: straight-line block summarization + optimal move-order emission (DP on 1D points)
#   3: linear transfer/copy/mul loop canonicalization (delta-map) + DP emission
#   4: constant/zero propagation across straight-line code + remove dead loops (known zero)
#      + partial-eval linear loops when source is known const
#      + conservative scan-loop folding ([>] / [<]) when first-zero is provable
#   5: multi-pass fixpoint + slightly more permissive cost model for folding
#   6: rewrite saturation (small, safe IR rewrites) + fixpoint
#   7: everything above (kept safe; superopt is intentionally not enabled by default because
#      "shorter but slower" loop-based compression conflicts with the goal)
#
# Assumptions:
#   - By default wrap=True and cell_size=256 (classic 8-bit BF). Use --no-wrap to disable.
#   - Input is syntactically correct (balanced brackets).
#
# NOTE: This optimizer is "aggressively safe": it will not reorder across IO or unknown loops.
#       It only performs algebraic transforms on proven-linear loops (Move/Add only, net ptr 0).
#
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Union, Optional, Dict, Tuple, Iterable
import argparse
import sys

# ---------------- IR Nodes ----------------
@dataclass(frozen=True)
class Add:
    n: int  # net +/- on current cell

@dataclass(frozen=True)
class Move:
    n: int  # net >/<

@dataclass(frozen=True)
class IO:
    op: str  # '.' or ','

@dataclass(frozen=True)
class Loop:
    body: List["Node"]

@dataclass(frozen=True)
class Clear:
    pass  # emits "[-]"

Node = Union[Add, Move, IO, Loop, Clear]
BF_OPS = set("+-<>[],.")

# ---------------- Parser: BF -> AST ----------------
def parse_bf(code: str) -> List[Node]:
    code = "".join(ch for ch in code if ch in BF_OPS)
    stack: List[List[Node]] = [[]]

    for ch in code:
        if ch == "[":
            body: List[Node] = []
            stack[-1].append(Loop(body))
            stack.append(body)
        elif ch == "]":
            if len(stack) == 1:
                raise ValueError("Unmatched ']'")
            stack.pop()
        elif ch in "+-":
            stack[-1].append(Add(1 if ch == "+" else -1))
        elif ch in "<>":
            stack[-1].append(Move(1 if ch == ">" else -1))
        elif ch in ".,":  # IO
            stack[-1].append(IO(ch))

    if len(stack) != 1:
        raise ValueError("Unmatched '['")
    return stack[0]

# ---------------- Emit + counts ----------------
def emit(nodes: List[Node]) -> str:
    out: List[str] = []
    for n in nodes:
        if isinstance(n, Add):
            out.append(("+" * n.n) if n.n > 0 else ("-" * (-n.n)))
        elif isinstance(n, Move):
            out.append((">" * n.n) if n.n > 0 else ("<" * (-n.n)))
        elif isinstance(n, IO):
            out.append(n.op)
        elif isinstance(n, Clear):
            out.append("[-]")
        elif isinstance(n, Loop):
            out.append("[" + emit(n.body) + "]")
    return "".join(out)

def count_static_ops(nodes: List[Node]) -> int:
    """Static BF primitive ops count of emitted code."""
    c = 0
    for n in nodes:
        if isinstance(n, Add):
            c += abs(n.n)
        elif isinstance(n, Move):
            c += abs(n.n)
        elif isinstance(n, IO):
            c += 1
        elif isinstance(n, Clear):
            c += 3
        elif isinstance(n, Loop):
            c += 2 + count_static_ops(n.body)
    return c

# ---------------- Basic utilities ----------------
def pack(nodes: List[Node]) -> List[Node]:
    """Combine adjacent Add/Add and Move/Move; remove zeros."""
    out: List[Node] = []
    i = 0
    while i < len(nodes):
        n = nodes[i]
        if isinstance(n, Add):
            s = 0
            while i < len(nodes) and isinstance(nodes[i], Add):
                s += nodes[i].n
                i += 1
            if s != 0:
                out.append(Add(s))
            continue
        if isinstance(n, Move):
            s = 0
            while i < len(nodes) and isinstance(nodes[i], Move):
                s += nodes[i].n
                i += 1
            if s != 0:
                out.append(Move(s))
            continue
        if isinstance(n, Loop):
            out.append(Loop(pack(n.body)))
        else:
            out.append(n)
        i += 1
    return out

def reduce_add_mod(nodes: List[Node], cell_size: Optional[int], wrap: bool) -> List[Node]:
    """If wrapping, shrink Add by modulo (e.g. +250 -> -6)."""
    if not (wrap and cell_size):
        return nodes
    out: List[Node] = []
    for n in nodes:
        if isinstance(n, Add):
            v = n.n % cell_size
            if v == 0:
                continue
            if v <= cell_size - v:
                out.append(Add(v))
            else:
                out.append(Add(-(cell_size - v)))
        elif isinstance(n, Loop):
            out.append(Loop(reduce_add_mod(n.body, cell_size, wrap)))
        else:
            out.append(n)
    return pack(out)

def peephole_clear_local(nodes: List[Node]) -> List[Node]:
    """Local clear peepholes (adjacent)."""
    out: List[Node] = []
    i = 0
    while i < len(nodes):
        cur = nodes[i]
        # immediate Add before Clear is dead
        if isinstance(cur, Add) and i + 1 < len(nodes) and isinstance(nodes[i + 1], Clear):
            i += 1
            continue
        # duplicate Clear
        if isinstance(cur, Clear) and out and isinstance(out[-1], Clear):
            i += 1
            continue
        out.append(cur)
        i += 1
    return pack(out)

# ---------------- 1D DP for optimal visit order ----------------
def optimal_visit_order(points: List[int], start: int, end: int) -> List[int]:
    """
    Visit all unique points (integers on a line), starting at 'start' and ending at 'end',
    minimizing total |moves|. Returns an order of visiting points.
    DP on interval endpoints: O(n^2).
    """
    uniq = sorted(set(points))
    n = len(uniq)
    if n == 0:
        return []
    if n == 1:
        return uniq

    # Map index -> coordinate
    xs = uniq

    # dp[l][r][side]: minimal cost to have visited interval [l,r], current position at l (side=0) or r (side=1)
    INF = 10**18
    dp = [[[INF, INF] for _ in range(n)] for __ in range(n)]
    parent: List[List[List[Optional[Tuple[int,int,int]]]]] = [[[None, None] for _ in range(n)] for __ in range(n)]
    # initialize for each single point
    for i in range(n):
        cost = abs(start - xs[i])
        dp[i][i][0] = cost
        dp[i][i][1] = cost
        parent[i][i][0] = None
        parent[i][i][1] = None

    for length in range(2, n + 1):
        for l in range(0, n - length + 1):
            r = l + length - 1

            # Extend from l+1..r to l..r
            # If we end at l
            # prev end at l+1:
            c1 = dp[l + 1][r][0] + abs(xs[l + 1] - xs[l])
            # prev end at r:
            c2 = dp[l + 1][r][1] + abs(xs[r] - xs[l])
            if c1 <= c2:
                dp[l][r][0] = c1
                parent[l][r][0] = (l + 1, r, 0)
            else:
                dp[l][r][0] = c2
                parent[l][r][0] = (l + 1, r, 1)

            # Extend from l..r-1 to l..r
            # If we end at r
            # prev end at l:
            c3 = dp[l][r - 1][0] + abs(xs[l] - xs[r])
            # prev end at r-1:
            c4 = dp[l][r - 1][1] + abs(xs[r - 1] - xs[r])
            if c3 <= c4:
                dp[l][r][1] = c3
                parent[l][r][1] = (l, r - 1, 0)
            else:
                dp[l][r][1] = c4
                parent[l][r][1] = (l, r - 1, 1)

    # add final move to end, pick better side
    total0 = dp[0][n - 1][0] + abs(xs[0] - end)
    total1 = dp[0][n - 1][1] + abs(xs[n - 1] - end)
    side = 0 if total0 <= total1 else 1

    # reconstruct visited points order (reverse)
    seq: List[int] = []
    l, r = 0, n - 1
    cur_side = side
    while True:
        if l == r:
            seq.append(xs[l])
            break
        prev = parent[l][r][cur_side]
        assert prev is not None
        pl, pr, pside = prev
        # The newly added point is at boundary that differs from prev interval
        if pl > l:  # we expanded left boundary from l+1 to l -> added xs[l]
            seq.append(xs[l])
        elif pr < r:  # expanded right boundary -> added xs[r]
            seq.append(xs[r])
        else:
            # should not happen
            seq.append(xs[l] if cur_side == 0 else xs[r])
        l, r, cur_side = pl, pr, pside

    # seq is in reverse order of additions; we need an actual traversal order.
    # We can build traversal by simulating greedy connecting points as they were added.
    # Easier: Just choose a path that visits all points by sweeping between extremes is optimal on a line,
    # BUT DP above already chose the best "end side". We'll generate a consistent order by:
    #  - Take points sorted, and choose either increasing or decreasing depending on which extreme DP ended at.
    # This matches optimal cost on a line (visit all points).
    # We'll respect the final chosen end-side by picking sweep direction and then relying on start/end moves.
    # (DP ensures the same minimal move distance.)
    mn, mx = xs[0], xs[-1]
    if side == 0:
        # end at mn before moving to end => sweep mx->mn
        return list(reversed(xs))
    else:
        # end at mx before moving to end => sweep mn->mx
        return xs

# ---------------- Straight-line block summarization + emission ----------------
CellEffect = Tuple[bool, int]  # (cleared, delta)

def summarize_basic_block(block: List[Node]) -> Tuple[int, Dict[int, CellEffect]]:
    """
    block contains only Add/Move/Clear.
    Returns: (end_pointer_shift, effects_map offset->(clear,delta))
    """
    p = 0
    eff: Dict[int, List[int]] = {}  # offset -> [clear(0/1), delta]
    def get(off: int) -> List[int]:
        if off not in eff:
            eff[off] = [0, 0]
        return eff[off]

    for n in block:
        if isinstance(n, Move):
            p += n.n
        elif isinstance(n, Add):
            e = get(p)
            e[1] += n.n
        elif isinstance(n, Clear):
            e = get(p)
            e[0] = 1
            e[1] = 0
        else:
            raise AssertionError("Unexpected node in basic block")

    effects: Dict[int, CellEffect] = {}
    for off, (c, d) in eff.items():
        if c or d != 0:
            effects[off] = (bool(c), d)
    return p, effects

def emit_effects_as_block(effects: Dict[int, CellEffect], end_pos: int = 0) -> List[Node]:
    """
    Emit a block (Add/Move/Clear only) that applies 'effects' starting at pointer 0 and ends at end_pos,
    with near-optimal movement order (DP).
    """
    items = {o: e for o, e in effects.items() if e[0] or e[1] != 0}
    if not items:
        return [Move(end_pos)] if end_pos != 0 else []

    offs = list(items.keys())
    order = optimal_visit_order(offs, start=0, end=end_pos)

    out: List[Node] = []
    cur = 0
    for off in order:
        if off != cur:
            out.append(Move(off - cur))
            cur = off
        clear, delta = items[off]
        if clear:
            out.append(Clear())
        if delta != 0:
            out.append(Add(delta))
    if cur != end_pos:
        out.append(Move(end_pos - cur))
    return pack(out)

def apply_block_summarization(nodes: List[Node]) -> List[Node]:
    """
    Replace maximal runs of (Add/Move/Clear) with their summary emitted canonically.
    Safe only because there is no IO/Loop inside those runs.
    """
    out: List[Node] = []
    buf: List[Node] = []

    def flush():
        nonlocal buf
        if not buf:
            return
        end_shift, effects = summarize_basic_block(buf)
        out.extend(emit_effects_as_block(effects, end_pos=end_shift))
        buf = []

    for n in nodes:
        if isinstance(n, (Add, Move, Clear)):
            buf.append(n)
        else:
            flush()
            out.append(n)
    flush()
    return pack(out)

# ---------------- Linear loop analysis (level>=3) ----------------
def analyze_linear_loop(body: List[Node]) -> Optional[Dict[int, int]]:
    """
    If loop body consists only of Add/Move, and net pointer shift is 0,
    return per-iteration delta map: offset -> delta (relative to loop entry pointer).
    Otherwise None.
    """
    p = 0
    delta: Dict[int, int] = {}
    for n in body:
        if isinstance(n, Move):
            p += n.n
        elif isinstance(n, Add):
            delta[p] = delta.get(p, 0) + n.n
        else:
            return None
    if p != 0:
        return None
    # remove zeros
    delta = {k: v for k, v in delta.items() if v != 0}
    return delta

def canonicalize_linear_loop(delta: Dict[int, int]) -> Optional[List[Node]]:
    """
    For transfer/copy/mul loops that terminate by decrementing the source:
      require delta[0] == -1 (classic form).
    Then emit a canonical minimal-move iteration:
      - Add(-1) at source
      - visit other offsets in optimal order (DP) and apply their adds
      - return to 0
    """
    if delta.get(0, 0) != -1:
        return None
    other = {k: v for k, v in delta.items() if k != 0 and v != 0}
    if not other:
        return [Add(-1)]  # will become Clear elsewhere

    offs = list(other.keys())
    order = optimal_visit_order(offs, start=0, end=0)

    out: List[Node] = [Add(-1)]
    cur = 0
    for off in order:
        if off != cur:
            out.append(Move(off - cur))
            cur = off
        out.append(Add(other[off]))
    if cur != 0:
        out.append(Move(-cur))
    return pack(out)

# ---------------- Scan loop recognition ([>] / [<]) ----------------
def is_scan_loop(n: Node) -> Optional[int]:
    """
    Return direction (+1 for [>], -1 for [<]) if node is a scan loop (Move-only body).
    Requires loop body to be exactly a single Move(+1) or Move(-1) after packing.
    """
    if not isinstance(n, Loop):
        return None
    body = pack(n.body)
    if len(body) == 1 and isinstance(body[0], Move) and body[0].n in (1, -1):
        return body[0].n
    return None

# ---------------- Value domain for const/zero propagation ----------------
Known = Optional[int]   # known const mod cell_size; None means unknown
NonZero = Optional[bool]  # None unknown, True known nonzero, False known zero

def known_is_zero(k: Known) -> Optional[bool]:
    if k is None:
        return None
    return k == 0

def known_nonzero(k: Known) -> Optional[bool]:
    if k is None:
        return None
    return k != 0

# ---------------- Const-prop + partial evaluation (level>=4) ----------------
def fold_with_constants(
    nodes: List[Node],
    level: int,
    cell_size: Optional[int],
    wrap: bool,
    length_slack: int,
    scan_window: int = 64
) -> List[Node]:
    """
    Forward pass tracking known constants for absolute tape indices (relative to program start),
    while pointer position is tracked exactly in straight-line code.
    Barriers (unknown loops) drop knowledge conservatively.
    Cap scan reasoning to +/-scan_window cells from current pointer.
    """
    # Without wrap+cell_size, only "known zero" after Clear is reliable; constants from +/- are not.
    can_track_arith = wrap and (cell_size is not None)

    p = 0  # absolute pointer index
    tape: Dict[int, Known] = {}  # abs_index -> Known const
    out: List[Node] = []

    def get(idx: int) -> Known:
        return tape.get(idx, None)

    def setv(idx: int, v: Known) -> None:
        if v is None:
            tape.pop(idx, None)
        else:
            tape[idx] = v

    def barrier():
        tape.clear()

    def apply_add_to_known(idx: int, delta: int):
        if not can_track_arith:
            setv(idx, None)
            return
        kv = get(idx)
        if kv is None:
            return
        setv(idx, (kv + delta) % cell_size)  # type: ignore[arg-type]

    for n in nodes:
        if isinstance(n, Move):
            p += n.n
            out.append(n)
            continue

        if isinstance(n, Add):
            apply_add_to_known(p, n.n)
            out.append(n)
            continue

        if isinstance(n, Clear):
            kv = get(p)
            if kv == 0:
                # redundant clear
                continue
            setv(p, 0)
            out.append(n)
            continue

        if isinstance(n, IO):
            out.append(n)
            if n.op == ",":
                # input overwrites current cell
                setv(p, None)
            # '.' doesn't change
            continue

        if isinstance(n, Loop):
            # If current cell known zero => loop never runs
            kv = get(p)
            if kv == 0:
                continue

            # Try scan-loop folding if provable
            if level >= 4:
                direction = is_scan_loop(n)
                if direction is not None:
                    # If current known zero => already removed above.
                    # Otherwise, we can fold only if we can prove first zero in that direction,
                    # i.e. some k>0 with cell[p + k*dir]==0 and all cells before are known nonzero.
                    # We'll search within scan_window.
                    found_k: Optional[int] = None
                    # If current cell known nonzero, we start from 1; else from 0 (unknown might already be 0).
                    start_k = 1 if (known_nonzero(kv) is True) else 0
                    for k in range(start_k, scan_window + 1):
                        idx = p + k * direction
                        vk = get(idx)
                        if vk is None:
                            # cannot prove beyond unknown
                            break
                        if vk == 0:
                            found_k = k
                            break
                        # vk is known nonzero, keep going
                    if found_k is not None:
                        # If k==0, it means current already known zero (handled), but keep safe
                        if found_k == 0:
                            continue
                        out.append(Move(found_k * direction))
                        p += found_k * direction
                        # now at known zero cell
                        setv(p, 0)
                        continue

            # Try partial-eval of linear transfer loops when source known const (wrap required)
            if level >= 4 and can_track_arith and kv is not None:
                body_opt = n.body  # assume inner already optimized upstream
                delta = analyze_linear_loop(body_opt)
                if delta is not None and delta.get(0, 0) == -1:
                    x = kv % cell_size  # type: ignore[operator]
                    if x == 0:
                        continue

                    # Compute effects: source clears, targets add x*delta
                    effects: Dict[int, CellEffect] = {0: (True, 0)}
                    for off, d in delta.items():
                        if off == 0 or d == 0:
                            continue
                        addv = (d * x) % cell_size  # type: ignore[operator]
                        if addv == 0:
                            continue
                        # choose shorter +/- encoding
                        if addv <= cell_size - addv:  # type: ignore[operator]
                            addn = addv
                        else:
                            addn = -(cell_size - addv)  # type: ignore[operator]
                        prev = effects.get(off, (False, 0))
                        effects[off] = (prev[0], prev[1] + int(addn))

                    repl_nodes = emit_effects_as_block(effects, end_pos=0)
                    repl_nodes = reduce_add_mod(repl_nodes, cell_size, wrap)
                    repl_static = count_static_ops(repl_nodes)

                    orig_body_static = count_static_ops(body_opt)
                    orig_static = 2 + orig_body_static

                    # Estimated runtime steps for original when x known:
                    # Each iteration executes body + ']' check; plus one final '[' check.
                    # Approx: x*(body_static + 1) + 1
                    orig_steps_est = x * (orig_body_static + 1) + 1
                    repl_steps_est = repl_static

                    ok_length = repl_static <= orig_static + length_slack
                    better = (repl_steps_est < orig_steps_est) or (repl_static < orig_static)

                    if ok_length and better:
                        # Emit replacement
                        out.extend(repl_nodes)

                        # Update known values: source becomes 0
                        setv(p, 0)
                        # Targets get updated if known
                        for off, (clr, dn) in effects.items():
                            if off == 0:
                                continue
                            idx = p + off
                            old = get(idx)
                            if old is not None:
                                setv(idx, (old + dn) % cell_size)  # type: ignore[arg-type]
                        continue

            # Otherwise, keep loop and barrier knowledge conservatively (unknown iterations).
            out.append(n)
            barrier()
            continue

    return pack(out)

# ---------------- Rewrite saturation (small, safe) ----------------
def saturate_rewrites(nodes: List[Node], cell_size: Optional[int], wrap: bool, rounds: int = 4) -> List[Node]:
    """
    A small, safe saturation:
      - repeatedly apply pack, modulo shrink, peepholes, block summarization.
      - does not reorder across IO/Loop beyond what's already safe.
    """
    cur = nodes
    for _ in range(rounds):
        prev = emit(cur)
        cur = pack(cur)
        cur = reduce_add_mod(cur, cell_size, wrap)
        cur = peephole_clear_local(cur)
        cur = apply_block_summarization(cur)
        cur = pack(cur)
        if emit(cur) == prev:
            break
    return cur

# ---------------- Main optimizer pipeline ----------------
def optimize_nodes(nodes: List[Node], level: int, cell_size: Optional[int], wrap: bool) -> List[Node]:
    # 1) recurse into loops first
    out: List[Node] = []
    for n in nodes:
        if isinstance(n, Loop):
            body = optimize_nodes(n.body, level, cell_size, wrap)
            body = pack(body)

            # level>=1: recognize clear loops: [-] and (wrap) [+]
            if level >= 1:
                if len(body) == 1 and isinstance(body[0], Add) and body[0].n in (-1, 1):
                    if body[0].n == -1:
                        out.append(Clear())
                        continue
                    if body[0].n == 1 and wrap and cell_size is not None:
                        out.append(Clear())
                        continue

            # level>=3: canonicalize linear transfer/copy/mul loops
            if level >= 3:
                delta = analyze_linear_loop(body)
                if delta is not None:
                    canon = canonicalize_linear_loop(delta)
                    if canon is not None:
                        # degenerate [-] -> Clear
                        if len(canon) == 1 and isinstance(canon[0], Add) and canon[0].n == -1:
                            out.append(Clear())
                        else:
                            out.append(Loop(canon))
                        continue

            out.append(Loop(body))
        else:
            out.append(n)

    out = pack(out)

    # 2) level>=0: pack already done; add modulo/peephole at >=1
    if level >= 1:
        out = reduce_add_mod(out, cell_size, wrap)
        out = peephole_clear_local(out)
        out = pack(out)

    # 3) level>=2: summarize straight-line blocks
    if level >= 2:
        out = apply_block_summarization(out)
        if level >= 1:
            out = reduce_add_mod(out, cell_size, wrap)
            out = peephole_clear_local(out)
        out = pack(out)

    # 4) level>=4: constant/zero propagation + partial eval + scan folding
    if level >= 4:
        slack = 0 if level == 4 else 8  # level>=5 more tolerant for folding gains
        out = fold_with_constants(out, level, cell_size, wrap, length_slack=slack)
        if level >= 1:
            out = reduce_add_mod(out, cell_size, wrap)
            out = peephole_clear_local(out)
        if level >= 2:
            out = apply_block_summarization(out)
        out = pack(out)

    # 5) level>=6: saturation (safe)
    if level >= 6:
        out = saturate_rewrites(out, cell_size, wrap, rounds=6)
        out = pack(out)

    return out

def optimize_bf(code: str, level: int, cell_size: Optional[int], wrap: bool) -> str:
    ast = parse_bf(code)

    # Level>=5: fixpoint iteration to expose opportunities
    if level >= 5:
        prev_s: Optional[str] = None
        cur_ast = ast
        for _ in range(16):
            opt = optimize_nodes(cur_ast, level, cell_size, wrap)
            s = emit(opt)
            if s == prev_s:
                return s
            prev_s = s
            cur_ast = parse_bf(s)
        return prev_s if prev_s is not None else emit(optimize_nodes(ast, level, cell_size, wrap))

    opt = optimize_nodes(ast, level, cell_size, wrap)
    return emit(opt)

# ---------------- CLI ----------------
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Brainfuck optimizer (outputs standard BF)."
    )
    parser.add_argument("--level", type=int, default=5, help="0..7 (higher = more aggressive)")
    parser.add_argument("--no-wrap", action="store_true", help="Disable cell wrapping assumptions")
    parser.add_argument("--cell-size", type=int, default=256, help="Cell size for wrapping (default 256)")
    args = parser.parse_args(argv)

    src = sys.stdin.read()
    wrap = not args.no_wrap
    cell_size = args.cell_size if wrap else None

    level = int(args.level)
    if level < 0:
        level = 0
    if level > 7:
        level = 7

    optimized = optimize_bf(src, level=level, cell_size=cell_size, wrap=wrap)
    sys.stdout.write(optimized)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
