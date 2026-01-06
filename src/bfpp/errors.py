from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


def _build_context(lines: List[str], line_no_1: int, *, context: int = 2) -> str:
    idx = max(1, line_no_1)
    start = max(1, idx - context)
    end = min(len(lines), idx + context)

    out: List[str] = []
    for i in range(start, end + 1):
        prefix = '>' if i == idx else ' '
        out.append(f"{prefix} {i:4d} | {lines[i - 1]}")
    return "\n".join(out)


def _hint_for(message: str, *, kind: str) -> Optional[str]:
    msg = message.lower()
    if kind == 'preprocess':
        if 'unknown preprocessor directive' in msg:
            return 'Only #define and #undef are supported. Directives must start at the beginning of the line.'
        if 'macro expansion limit exceeded' in msg:
            return 'Check for recursive macros (directly or indirectly).'
        if 'expects' in msg and 'args' in msg:
            return 'Check the macro call argument count and parentheses. Example: MACRO() for zero-arg macros.'
        if 'unterminated macro' in msg:
            return 'Check for a missing closing ")" in a macro invocation.'
        return None
    if kind == 'compile':
        if 'unknown variable' in msg:
            return 'Declare the variable first (declare byte/char/int/string...) and check spelling.'
        if 'mismatched parentheses' in msg:
            return 'Check for missing ")" or an extra "(" in the statement.'
        if 'invalid condition' in msg:
            return 'Conditions must be of the form: (x), (x == 1), (x != 1), (x < 1), etc.'
        return None
    return None


@dataclass
class BFPPError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


@dataclass
class BFPPPreprocessError(BFPPError):
    line: int
    context: str


@dataclass
class BFPPCompileError(BFPPError):
    line: int
    context: str


def make_preprocess_error(*, message: str, source: str, line: int) -> BFPPPreprocessError:
    lines = source.split('\n')
    ctx = _build_context(lines, line)
    hint = _hint_for(message, kind='preprocess')
    hint_block = f"\nHint: {hint}" if hint else ""
    return BFPPPreprocessError(
        message=f"PreprocessError: {message} (line {line})\n{ctx}{hint_block}",
        line=line,
        context=ctx,
    )


def make_compile_error(*, message: str, source: str, line: int) -> BFPPCompileError:
    lines = source.split('\n')
    ctx = _build_context(lines, line)
    hint = _hint_for(message, kind='compile')
    hint_block = f"\nHint: {hint}" if hint else ""
    return BFPPCompileError(
        message=f"CompileError: {message} (line {line})\n{ctx}{hint_block}",
        line=line,
        context=ctx,
    )
