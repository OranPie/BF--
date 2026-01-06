import re

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .errors import make_preprocess_error


@dataclass
class _Macro:
    name: str
    params: Optional[Tuple[str, ...]]
    replacement: Tuple[str, ...]


def _strip_comments(code: str) -> str:
    code = re.sub(r'//.*', '', code)
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    return code


def _parse_define_tokens(tokens: List[str]) -> _Macro:
    if len(tokens) < 2:
        raise ValueError('Invalid macro definition')
    name = tokens[1]
    if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name):
        raise ValueError(f'Invalid macro name: {name}')

    if len(tokens) >= 3 and tokens[2] == '(':
        depth = 0
        params: List[str] = []
        cur: List[str] = []
        i = 2
        while i < len(tokens):
            t = tokens[i]
            if t == '(':
                depth += 1
                if depth == 1:
                    i += 1
                    continue
            if t == ')':
                depth -= 1
                if depth == 0:
                    if cur:
                        params.append(''.join(cur).strip())
                    i += 1
                    break
            if depth == 1 and t == ',':
                params.append(''.join(cur).strip())
                cur = []
                i += 1
                continue
            if depth == 1:
                cur.append(t)
                i += 1
                continue
            i += 1

        if depth != 0:
            raise ValueError('Unterminated macro parameter list')

        params_clean: List[str] = []
        for p in params:
            if not p:
                continue
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', p):
                raise ValueError(f'Invalid macro parameter: {p}')
            params_clean.append(p)
        replacement = tuple(tokens[i:])
        return _Macro(name=name, params=tuple(params_clean), replacement=replacement)

    return _Macro(name=name, params=None, replacement=tuple(tokens[2:]))


def _split_macro_args(tokens: List[str], start_idx: int) -> Tuple[List[List[str]], int]:
    if start_idx >= len(tokens) or tokens[start_idx] != '(':
        raise ValueError('Expected macro argument list')
    args: List[List[str]] = []
    cur: List[str] = []
    depth = 0
    i = start_idx
    while i < len(tokens):
        t = tokens[i]
        if t == '(':
            depth += 1
            if depth > 1:
                cur.append(t)
            i += 1
            continue
        if t == ')':
            depth -= 1
            if depth == 0:
                if not args and not cur:
                    return [], i
                if args and not cur:
                    raise ValueError('Empty macro argument')
                args.append(cur)
                return args, i
            cur.append(t)
            i += 1
            continue
        if t == ',' and depth == 1:
            if not cur:
                raise ValueError('Empty macro argument')
            args.append(cur)
            cur = []
            i += 1
            continue
        cur.append(t)
        i += 1

    raise ValueError('Unterminated macro invocation')


def _expand_tokens(tokens: List[str], macros: Dict[str, _Macro], *, depth: int, max_depth: int) -> List[str]:
    if depth > max_depth:
        raise RecursionError('Macro expansion limit exceeded')

    out: List[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]

        if t.startswith('"') and t.endswith('"'):
            out.append(t)
            i += 1
            continue

        m = macros.get(t)
        if m is None:
            out.append(t)
            i += 1
            continue

        if m.params is None:
            repl = list(m.replacement)
            out.extend(_expand_tokens(repl, macros, depth=depth + 1, max_depth=max_depth))
            i += 1
            continue

        if i + 1 >= len(tokens) or tokens[i + 1] != '(':
            out.append(t)
            i += 1
            continue

        args, end_idx = _split_macro_args(tokens, i + 1)
        params = list(m.params)
        if len(args) != len(params):
            raise ValueError(f"Macro '{m.name}' expects {len(params)} args, got {len(args)}")

        arg_map: Dict[str, List[str]] = {}
        for p, a in zip(params, args):
            arg_map[p] = _expand_tokens(a, macros, depth=depth + 1, max_depth=max_depth)

        substituted: List[str] = []
        for rt in m.replacement:
            if rt in arg_map:
                substituted.extend(arg_map[rt])
            else:
                substituted.append(rt)

        out.extend(_expand_tokens(substituted, macros, depth=depth + 1, max_depth=max_depth))
        i = end_idx + 1

    return out


def _process_macros(code: str) -> str:
    macros: Dict[str, _Macro] = {}
    out_lines: List[str] = []
    max_depth = 50

    code_lines = code.split('\n')
    for line_no_0, raw_line in enumerate(code_lines):
        line = raw_line.rstrip('\n')
        stripped = line.strip()

        if not stripped:
            out_lines.append('')
            continue

        try:
            if stripped.startswith('#'):
                directive_tokens = tokenize(stripped)
                if not directive_tokens:
                    continue

                head = directive_tokens[0]
                if head == '#define':
                    m = _parse_define_tokens(directive_tokens)
                    macros[m.name] = m
                    continue
                if head == '#undef':
                    if len(directive_tokens) < 2:
                        raise ValueError('Invalid #undef')
                    macros.pop(directive_tokens[1], None)
                    continue

                raise ValueError(f'Unknown preprocessor directive: {head}')

            toks = tokenize(line)
            expanded = _expand_tokens(toks, macros, depth=0, max_depth=max_depth)
            out_lines.append(' '.join(expanded))
        except Exception as e:
            raise make_preprocess_error(message=f"{type(e).__name__}: {e}", source='\n'.join(code_lines), line=line_no_0 + 1) from e

    return '\n'.join(out_lines)


def preprocess(code: str) -> str:
    code = _strip_comments(code)
    return _process_macros(code)


def tokenize(line: str):
    tokens = []
    i = 0
    while i < len(line):
        if line[i].isspace():
            i += 1
            continue

        if line[i] == '"':
            j = i + 1
            while j < len(line) and line[j] != '"':
                j += 1
            tokens.append(line[i:j + 1])
            i = j + 1
        elif line[i:i + 2] in {"==", ">=", "<=", "!="}:
            tokens.append(line[i:i + 2])
            i += 2
        elif line[i] in '{}()[]<>,;=!&|~+-*/%':
            tokens.append(line[i])
            i += 1
        else:
            j = i
            while j < len(line) and not line[j].isspace() and line[j] not in '{}()[]<>,;=!&|~+-*/%':
                j += 1
            tokens.append(line[i:j])
            i = j

    return tokens
