from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class CompilerState:
    variables: Dict[str, dict] = field(default_factory=dict)
    current_ptr: int = 0
    max_ptr: int = 0
    temp_cells: List[Tuple[int, int]] = field(default_factory=list)
    bf_code: List[str] = field(default_factory=list)
    loop_condition_stack: List[int] = field(default_factory=list)
    optimize_level: Optional[int] = None

    def reset(self, *, optimize_level: Optional[int] = None) -> None:
        self.variables.clear()
        self.current_ptr = 0
        self.max_ptr = 0
        self.temp_cells.clear()
        self.bf_code.clear()
        self.loop_condition_stack.clear()
        if optimize_level is not None:
            self.optimize_level = optimize_level
