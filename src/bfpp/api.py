from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from .compiler import BrainFuckPlusPlusCompiler


@dataclass(frozen=True)
class CompileOptions:
    optimize_level: Optional[int] = None


@dataclass(frozen=True)
class CompileResult:
    bf_code: str
    variables: Dict[str, Dict[str, Any]]
    max_ptr: int


def compile_string(source: str, *, options: Optional[CompileOptions] = None) -> CompileResult:
    opt_level = None if options is None else options.optimize_level
    compiler = BrainFuckPlusPlusCompiler(optimize_level=opt_level)
    bf = compiler.compile(source, optimize_level=opt_level)
    return CompileResult(bf_code=bf, variables=dict(compiler.variables), max_ptr=int(compiler.max_ptr))


def compile_file(path: str | Path, *, options: Optional[CompileOptions] = None, encoding: str = "utf-8") -> CompileResult:
    p = Path(path)
    return compile_string(p.read_text(encoding=encoding), options=options)
