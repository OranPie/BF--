import sys
import time
import numpy as np
from numba import jit, njit
from PIL import Image, ImageDraw, ImageFont
import io
from concurrent.futures import ThreadPoolExecutor
import threading

# Attempt to import cv2, provide a message if it's not found for the export feature.
try:
    import cv2

    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QTableWidget, QTableWidgetItem, QPushButton, QSlider, QLabel, QSplitter,
    QHeaderView, QGroupBox, QStatusBar, QMessageBox, QLineEdit, QShortcut,
    QFileDialog, QProgressDialog
)
from PyQt5.QtCore import Qt, QTimer, QBuffer, QIODevice, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette, QTextCursor, QKeySequence, QPixmap, QImage
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


# Optimized JIT loop with better performance characteristics
@njit(cache=True, fastmath=True)
def jit_loop_optimized(program_arr, memory, pc, pointer, bracket_map_arr, max_steps=50000):
    """
    Highly optimized JIT-compiled BrainFuck execution loop.

    Improvements:
    - Increased default max_steps for better batching
    - Added fastmath=True for numerical operations
    - Optimized memory wrapping logic
    - Better branch prediction hints through code organization
    """
    stop_reason = 0
    mem_len = len(memory)
    prog_len = len(program_arr)
    steps = 0

    # Pre-calculate memory bounds to avoid repeated calculations
    mem_mask = mem_len - 1 if (mem_len & (mem_len - 1)) == 0 else -1

    while pc < prog_len and steps < max_steps:
        command = program_arr[pc]

        # Group related operations for better branch prediction
        if command == 62:  # '>'
            if mem_mask != -1:
                pointer = (pointer + 1) & mem_mask  # Fast modulo for power of 2
            else:
                pointer = (pointer + 1) % mem_len
        elif command == 60:  # '<'
            if mem_mask != -1:
                pointer = (pointer - 1) & mem_mask
            else:
                pointer = (pointer - 1) % mem_len
        elif command == 43:  # '+'
            memory[pointer] = (memory[pointer] + 1) & 255  # Faster than modulo
        elif command == 45:  # '-'
            memory[pointer] = (memory[pointer] - 1) & 255
        elif command == 46:  # '.'
            stop_reason = 1  # Stop for output
            break
        elif command == 44:  # ','
            stop_reason = 2  # Stop for input
            break
        elif command == 91:  # '['
            if memory[pointer] == 0:
                pc = bracket_map_arr[pc]
        elif command == 93:  # ']'
            if memory[pointer] != 0:
                pc = bracket_map_arr[pc]

        pc += 1
        steps += 1

    if pc >= prog_len:
        stop_reason = 3  # End of program
    elif steps >= max_steps:
        stop_reason = 4  # Max steps reached

    return pc, pointer, stop_reason, steps


# JIT-compiled function for bulk execution without I/O
@njit(cache=True, fastmath=True)
def jit_execute_bulk(program_arr, memory, pc, pointer, bracket_map_arr, target_steps):
    """
    Execute a specific number of steps without stopping for I/O.
    Used for video generation where we skip I/O operations.
    """
    mem_len = len(memory)
    prog_len = len(program_arr)
    steps = 0

    # Pre-calculate memory bounds
    mem_mask = mem_len - 1 if (mem_len & (mem_len - 1)) == 0 else -1

    while pc < prog_len and steps < target_steps:
        command = program_arr[pc]

        if command == 62:  # '>'
            if mem_mask != -1:
                pointer = (pointer + 1) & mem_mask
            else:
                pointer = (pointer + 1) % mem_len
        elif command == 60:  # '<'
            if mem_mask != -1:
                pointer = (pointer - 1) & mem_mask
            else:
                pointer = (pointer - 1) % mem_len
        elif command == 43:  # '+'
            memory[pointer] = (memory[pointer] + 1) & 255
        elif command == 45:  # '-'
            memory[pointer] = (memory[pointer] - 1) & 255
        elif command == 46 or command == 44:  # '.' or ','
            # Skip I/O operations in bulk execution
            pass
        elif command == 91:  # '['
            if memory[pointer] == 0:
                pc = bracket_map_arr[pc]
        elif command == 93:  # ']'
            if memory[pointer] != 0:
                pc = bracket_map_arr[pc]

        pc += 1
        steps += 1

    return pc, pointer, steps


class VideoExportThread(QThread):
    """Highly optimized video export thread."""
    progress_update = pyqtSignal(int)
    status_update = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, program_text, output_path, fps=30, duration=10):
        super().__init__()
        self.program_text = program_text
        self.output_path = output_path
        self.fps = fps
        self.duration = duration
        self.cancelled = False

        # Pre-allocate frame buffer for better memory management
        self.frame_width = 1200
        self.frame_height = 800
        self.frame_buffer = None

    def run(self):
        try:
            runner = BrainFuckRunner()
            runner.load_program(self.program_text)

            # Video settings
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(
                self.output_path, fourcc, self.fps,
                (self.frame_width, self.frame_height)
            )

            total_frames = self.fps * self.duration
            steps_per_frame = max(1, len(runner.program) // total_frames)

            self.status_update.emit("Initializing video export...")

            # Pre-compile font for better performance
            try:
                self.font = ImageFont.truetype("courier.ttf", 11)
                self.font_large = ImageFont.truetype("courier.ttf", 13)
                self.font_small = ImageFont.truetype("courier.ttf", 9)
            except:
                self.font = ImageFont.load_default()
                self.font_large = self.font
                self.font_small = self.font

            frames_generated = 0

            # Use ThreadPoolExecutor for parallel frame generation
            with ThreadPoolExecutor(max_workers=2) as executor:
                frame_futures = []

                for frame_idx in range(total_frames):
                    if self.cancelled:
                        break

                    # Execute steps for this frame
                    if runner.pc < len(runner.program):
                        if steps_per_frame > 1000:
                            # Use bulk execution for high step counts
                            runner.pc, runner.pointer, executed_steps = jit_execute_bulk(
                                runner.program_arr, runner.memory, runner.pc,
                                runner.pointer, runner.bracket_map_arr, steps_per_frame
                            )
                            runner.step_count += executed_steps
                        else:
                            # Use regular execution for smaller step counts
                            for _ in range(steps_per_frame):
                                if runner.pc >= len(runner.program):
                                    break
                                runner.step()

                    # Submit frame generation to thread pool
                    if len(frame_futures) < 4:  # Limit concurrent frames
                        future = executor.submit(self._create_frame_optimized, runner.copy_state())
                        frame_futures.append(future)

                    # Process completed frames
                    completed_futures = [f for f in frame_futures if f.done()]
                    for future in completed_futures:
                        frame = future.result()
                        video_writer.write(frame)
                        frames_generated += 1
                        frame_futures.remove(future)

                    # Update progress
                    progress = min(99, int(frames_generated * 100 / total_frames))
                    self.progress_update.emit(progress)

                    if frames_generated % 30 == 0:
                        self.status_update.emit(f"Generated {frames_generated}/{total_frames} frames...")

                # Process remaining frames
                for future in frame_futures:
                    if not self.cancelled:
                        frame = future.result()
                        video_writer.write(frame)
                        frames_generated += 1

            video_writer.release()

            if self.cancelled:
                self.finished_signal.emit(False, "Export cancelled")
            else:
                self.finished_signal.emit(True, f"Video exported: {frames_generated} frames to {self.output_path}")

        except Exception as e:
            self.finished_signal.emit(False, f"Error during export: {str(e)}")

    def _create_frame_optimized(self, runner_state):
        """Optimized frame generation with better layout and performance."""
        # Create image with better color scheme
        img = Image.new('RGB', (self.frame_width, self.frame_height), color=(25, 25, 25))
        draw = ImageDraw.Draw(img)

        pc, pointer, memory, step_count, output_buffer = runner_state
        y_offset = 15

        # Title with better styling
        draw.text((20, y_offset), "BrainFuck Execution Visualizer",
                  fill=(255, 255, 255), font=self.font_large)
        y_offset += 35

        # Status information in a more compact layout
        val = memory[pointer]
        ascii_char = chr(val) if 32 <= val <= 126 else '.'

        status_lines = [
            f"Step: {step_count:,}  |  PC: {pc}  |  Pointer: {pointer}  |  Value: {val} ('{ascii_char}')",
            f"Output: {''.join(output_buffer[-80:])}"  # Show more output
        ]

        for line in status_lines:
            draw.text((20, y_offset), line, fill=(200, 200, 200), font=self.font)
            y_offset += 22

        y_offset += 15

        # Memory visualization with improved layout
        draw.text((20, y_offset), "Memory Visualization:", fill=(180, 180, 180), font=self.font)
        y_offset += 25

        # Show more memory cells in a grid
        mem_start = max(0, pointer - 50)
        mem_end = min(len(memory), pointer + 50)

        x_start = 20
        y_start = y_offset
        cell_width = 45
        cell_height = 30
        cells_per_row = 25

        for i, addr in enumerate(range(mem_start, mem_end)):
            row = i // cells_per_row
            col = i % cells_per_row

            x = x_start + col * cell_width
            y = y_start + row * cell_height

            val = memory[addr]

            # Choose colors based on cell state
            if addr == pointer:
                # Pointer position - bright orange
                fill_color = (255, 165, 0)
                text_color = (0, 0, 0)
            elif val > 0:
                # Non-zero value - green gradient based on value
                intensity = min(255, 80 + val)
                fill_color = (40, intensity, 40)
                text_color = (255, 255, 255)
            else:
                # Zero value - dark gray
                fill_color = (60, 60, 60)
                text_color = (120, 120, 120)

            # Draw cell
            draw.rectangle([x, y, x + cell_width - 2, y + cell_height - 2],
                           fill=fill_color, outline=(100, 100, 100))

            # Draw value
            text = str(val)
            text_bbox = draw.textbbox((0, 0), text, font=self.font_small)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            text_x = x + (cell_width - text_width) // 2
            text_y = y + (cell_height - text_height) // 2

            draw.text((text_x, text_y), text, fill=text_color, font=self.font_small)

            # Draw address for pointer position
            if addr == pointer:
                addr_text = f"@{addr}"
                draw.text((x, y - 15), addr_text, fill=(255, 165, 0), font=self.font_small)

        # Convert PIL image to OpenCV format
        img_array = np.array(img)
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    def cancel(self):
        self.cancelled = True


class BrainFuckRunner:
    """Enhanced BrainFuck runner with fixed overflow issues."""

    def __init__(self):
        self.reset()

    def reset(self):
        # Use power-of-2 memory size for faster modulo operations
        self.memory = np.zeros(32768, dtype=np.uint8)  # 2^15 for fast bitwise operations
        self.pointer = 0
        self.pc = 0
        self.input_buffer = []
        self.output_buffer = []
        self.bracket_map = {}
        self.program = ""
        self.running = False
        self.step_count = 0
        self.history = []

        # Arrays for Numba
        self.program_arr = np.array([], dtype=np.int32)
        self.bracket_map_arr = np.array([], dtype=np.int32)

    def load_program(self, program_text):
        self.reset()
        # Filter out non-BrainFuck characters
        self.program = "".join(filter(lambda x: x in ['.', ',', '[', ']', '<', '>', '+', '-'], program_text))
        self.program_arr = np.array([ord(c) for c in self.program], dtype=np.int32)
        self._preprocess_brackets()

    def _preprocess_brackets(self):
        """Optimized bracket preprocessing."""
        self.bracket_map = {}
        stack = []

        for i, char in enumerate(self.program):
            if char == '[':
                stack.append(i)
            elif char == ']':
                if stack:
                    start = stack.pop()
                    self.bracket_map[start] = i
                    self.bracket_map[i] = start

        # Create NumPy array for Numba with proper initialization
        self.bracket_map_arr = np.arange(len(self.program), dtype=np.int32)
        for k, v in self.bracket_map.items():
            self.bracket_map_arr[k] = v

    def step(self):
        """
        Fixed single step execution without overflow errors.

        Returns:
            tuple: (continues_running, old_pointer, new_pointer, changed_mem_addr)
        """
        if self.pc >= len(self.program) or not self.running:
            return False, self.pointer, self.pointer, -1

        command = self.program[self.pc]
        self.step_count += 1

        # Only store history periodically to save memory
        if self.step_count % 10 == 0:
            self.history.append((self.step_count, self.pc))

        old_pointer = self.pointer
        mem_changed_addr = -1

        if command == '>':
            self.pointer = (self.pointer + 1) % len(self.memory)
        elif command == '<':
            self.pointer = (self.pointer - 1) % len(self.memory)
        elif command == '+':
            # Fixed: Use proper uint8 arithmetic to avoid overflow
            current_val = int(self.memory[self.pointer])
            self.memory[self.pointer] = np.uint8((current_val + 1) % 256)
            mem_changed_addr = self.pointer
        elif command == '-':
            # Fixed: Use proper uint8 arithmetic to avoid overflow
            current_val = int(self.memory[self.pointer])
            self.memory[self.pointer] = np.uint8((current_val - 1) % 256)
            mem_changed_addr = self.pointer
        elif command == '.':
            self.output_buffer.append(chr(self.memory[self.pointer]))
        elif command == ',':
            if self.input_buffer:
                input_char = self.input_buffer.pop(0)
                self.memory[self.pointer] = np.uint8(ord(input_char))
                mem_changed_addr = self.pointer
        elif command == '[':
            if self.memory[self.pointer] == 0:
                self.pc = self.bracket_map.get(self.pc, self.pc)
        elif command == ']':
            if self.memory[self.pointer] != 0:
                self.pc = self.bracket_map.get(self.pc, self.pc)

        self.pc += 1
        is_running = self.pc < len(self.program) and self.running
        return is_running, old_pointer, self.pointer, mem_changed_addr

    def run_jit_step(self):
        """Enhanced JIT execution with better step management."""
        if self.pc >= len(self.program_arr):
            return 3, None, 0

        # Create a copy for change detection
        mem_before = self.memory.copy()

        # Dynamic step calculation based on program complexity
        base_steps = 10000
        if self.running:
            # Increase steps for continuous execution
            max_steps = min(100000, base_steps * 2)
        else:
            max_steps = base_steps

        new_pc, new_pointer, stop_reason, steps = jit_loop_optimized(
            self.program_arr, self.memory, self.pc, self.pointer,
            self.bracket_map_arr, max_steps
        )

        # Efficiently find changed memory locations
        changed_indices = np.where(mem_before != self.memory)[0]

        self.step_count += steps
        self.pc = new_pc
        self.pointer = new_pointer

        # Update history less frequently for better performance
        if steps > 0:
            self.history.append((self.step_count, self.pc))

        if stop_reason == 1:  # Output
            self.output_buffer.append(chr(self.memory[self.pointer]))
            self.pc += 1
        elif stop_reason == 2:  # Input
            if self.input_buffer:
                input_char = self.input_buffer.pop(0)
                self.memory[self.pointer] = np.uint8(ord(input_char))
                changed_indices = np.append(changed_indices, self.pointer)
                self.pc += 1
            else:
                stop_reason = 5  # Paused for input

        return stop_reason, changed_indices, steps

    def copy_state(self):
        """Create a lightweight copy of the current state for video generation."""
        return (self.pc, self.pointer, self.memory.copy(),
                self.step_count, list(self.output_buffer))


class BrainFuckVisualizer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("BrainFuck Visualizer (JIT Enhanced Pro)")
        self.setGeometry(100, 100, 1400, 900)

        self.runner = BrainFuckRunner()
        self.execution_speed = 5
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.execute_step)

        self.JIT_THRESHOLD = 500  # Lower threshold for JIT activation
        self.export_thread = None

        # Performance monitoring
        self.last_update_time = time.time()
        self.performance_counter = 0

        self.init_ui()
        self.set_example_program()
        self.update_display_full()

    def init_ui(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        # --- Top Row: Code and Controls ---
        top_layout = QHBoxLayout()
        code_group = QGroupBox("BrainFuck Code")
        code_layout = QVBoxLayout(code_group)
        self.code_edit = QTextEdit()
        self.code_edit.setFont(QFont("Courier", 12))
        code_layout.addWidget(self.code_edit)

        control_group = QGroupBox("Controls")
        control_layout = QVBoxLayout(control_group)

        self.step_button = QPushButton("Step (F5)")
        self.run_button = QPushButton("Run/Pause (F6)")
        self.stop_button = QPushButton("Stop (F7)")
        self.reset_button = QPushButton("Reset (F8)")
        self.export_video_button = QPushButton("Export HD Video")

        self.step_button.clicked.connect(self.step_execution)
        self.run_button.clicked.connect(self.toggle_execution)
        self.stop_button.clicked.connect(self.stop_execution)
        self.reset_button.clicked.connect(self.reset_execution)
        self.export_video_button.clicked.connect(self.export_video)
        if not CV2_AVAILABLE:
            self.export_video_button.setEnabled(False)
            self.export_video_button.setToolTip("Please install opencv-python to enable video export.")

        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(1, 2000)  # Increased range
        self.speed_slider.setValue(self.execution_speed)
        self.speed_slider.valueChanged.connect(self.set_speed)
        self.speed_label = QLabel(f"{self.execution_speed} steps/s")
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_label)

        control_layout.addWidget(self.step_button)
        control_layout.addWidget(self.run_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.reset_button)
        control_layout.addWidget(self.export_video_button)
        control_layout.addLayout(speed_layout)
        control_layout.addStretch()

        top_layout.addWidget(code_group, 7)
        top_layout.addWidget(control_group, 3)
        main_layout.addLayout(top_layout, 2)

        # --- Bottom Splitter: Memory, I/O, Graph ---
        splitter = QSplitter(Qt.Vertical)

        memory_group = QGroupBox("Memory State")
        memory_layout = QVBoxLayout(memory_group)
        self.memory_table = QTableWidget()
        self.memory_table.setColumnCount(17)
        self.memory_table.setHorizontalHeaderLabels(["Address"] + [f"{i:02X}" for i in range(16)])
        self.memory_table.verticalHeader().setVisible(False)
        self.memory_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.memory_table.setFont(QFont("Courier", 10))
        memory_layout.addWidget(self.memory_table)

        output_group = QGroupBox("Output / Input")
        output_layout = QVBoxLayout(output_group)
        self.output_display = QTextEdit()
        self.output_display.setReadOnly(True)
        self.output_display.setFont(QFont("Courier", 12))
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Provide input for ',' command and press Enter")
        self.input_line.returnPressed.connect(self.update_input_buffer)
        output_layout.addWidget(self.output_display)
        output_layout.addWidget(self.input_line)

        graph_group = QGroupBox("Execution History & Performance")
        graph_layout = QVBoxLayout(graph_group)
        self.figure = Figure(facecolor='#353535')
        self.canvas = FigureCanvas(self.figure)
        graph_layout.addWidget(self.canvas)

        splitter.addWidget(memory_group)
        splitter.addWidget(output_group)
        splitter.addWidget(graph_group)
        splitter.setSizes([400, 200, 200])
        main_layout.addWidget(splitter, 5)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_info = QLabel("Ready")
        self.performance_info = QLabel("Performance: 0 steps/s")
        self.status_bar.addWidget(self.status_info)
        self.status_bar.addPermanentWidget(self.performance_info)

        # --- Shortcuts ---
        QShortcut(QKeySequence("F5"), self, self.step_execution)
        QShortcut(QKeySequence("F6"), self, self.toggle_execution)
        QShortcut(QKeySequence("Space"), self, self.toggle_execution)
        QShortcut(QKeySequence("F7"), self, self.stop_execution)
        QShortcut(QKeySequence("F8"), self, self.reset_execution)

    def set_example_program(self):
        # Classic "Hello World!" program
        code = "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]>>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+.>++."
        self.code_edit.setPlainText(code)

    def update_display_full(self):
        """Full refresh with performance optimizations."""
        self.runner.load_program(self.code_edit.toPlainText())
        self.update_memory_table_full()
        self.update_code_highlight()
        self.update_output_display()
        self.update_status_info()
        self.update_graph()
        self.input_line.clear()

    def update_status_info(self):
        val = int(self.runner.memory[self.runner.pointer])  # Convert to int for display
        ascii_char = chr(val) if 32 <= val <= 126 else '.'
        status = (f"PC: {self.runner.pc} | Pointer: {self.runner.pointer} | "
                  f"Instruction: '{self.get_current_instruction()}' | "
                  f"Value: {val} ('{ascii_char}') | Steps: {self.runner.step_count:,}")
        self.status_info.setText(status)

    def update_performance_info(self, steps_per_second):
        """Update performance counter in status bar."""
        mode = "JIT" if self.execution_speed > self.JIT_THRESHOLD else "Step"
        self.performance_info.setText(f"Performance: {steps_per_second:,.0f} steps/s ({mode})")

    def update_output_display(self):
        # Enhanced output display with better formatting
        output_text = ''.join(self.runner.output_buffer)
        if len(output_text) > 10000:  # Limit output length for performance
            output_text = "..." + output_text[-10000:]
        self.output_display.setPlainText(output_text)
        self.output_display.moveCursor(QTextCursor.End)

    def update_code_highlight(self):
        cursor = self.code_edit.textCursor()
        if self.runner.pc < len(self.runner.program):
            cursor.setPosition(self.runner.pc)
            cursor.movePosition(QTextCursor.Right, QTextCursor.KeepAnchor)

            extra_selections = []
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            selection.format.setBackground(QColor("orange"))
            extra_selections.append(selection)
            self.code_edit.setExtraSelections(extra_selections)
        else:
            self.code_edit.setExtraSelections([])

    def update_memory_table_full(self):
        """Optimized memory table initialization."""
        self.memory_table.clearContents()
        # Show fewer rows initially for better performance
        visible_rows = min(100, (len(self.runner.memory) + 15) // 16)
        self.memory_table.setRowCount(visible_rows)

        for r in range(visible_rows):
            addr_item = QTableWidgetItem(f"{r * 16:05X}")
            addr_item.setTextAlignment(Qt.AlignCenter)
            self.memory_table.setItem(r, 0, addr_item)
            for c in range(16):
                addr = r * 16 + c
                if addr < len(self.runner.memory):
                    item = QTableWidgetItem("0")
                    item.setTextAlignment(Qt.AlignCenter)
                    self.memory_table.setItem(r, c + 1, item)

        self.update_pointer_highlight(-1, self.runner.pointer)
        self.memory_table.resizeColumnsToContents()

    def update_memory_cell(self, addr):
        """Optimized memory cell update with proper value handling."""
        if addr < 0 or addr >= len(self.runner.memory):
            return

        row, col = divmod(addr, 16)
        if row >= self.memory_table.rowCount():
            return  # Outside visible range

        val = int(self.runner.memory[addr])  # Convert to int for display
        item = self.memory_table.item(row, col + 1)
        if not item:
            item = QTableWidgetItem()
            self.memory_table.setItem(row, col + 1, item)

        item.setText(str(val))

        # Optimized color setting
        if addr == self.runner.pointer:
            item.setBackground(QColor(255, 165, 0))
        elif val == 0:
            item.setBackground(QColor(50, 50, 50))
        else:
            # Color intensity based on value
            intensity = min(255, 70 + val)
            item.setBackground(QColor(intensity // 4, intensity, intensity // 4))

    def update_pointer_highlight(self, old_ptr, new_ptr):
        """Efficient pointer highlight update."""
        if old_ptr != -1:
            self.update_memory_cell(old_ptr)
        if new_ptr != -1:
            self.update_memory_cell(new_ptr)

    def update_graph(self):
        """Enhanced graph with performance metrics."""
        if not self.runner.history or len(self.runner.history) < 2:
            return

        self.figure.clear()

        # Create subplots
        ax1 = self.figure.add_subplot(211)
        ax2 = self.figure.add_subplot(212)

        # Style both axes
        for ax in [ax1, ax2]:
            ax.set_facecolor('#2b2b2b')
            ax.tick_params(axis='x', colors='white', labelsize=8)
            ax.tick_params(axis='y', colors='white', labelsize=8)
            for spine in ax.spines.values():
                spine.set_color('white')
            ax.xaxis.label.set_color('white')
            ax.yaxis.label.set_color('white')
            ax.title.set_color('white')

        # Plot execution trace
        recent_history = self.runner.history[-2000:]  # More history
        if recent_history:
            x, y = zip(*recent_history)
            ax1.plot(x, y, linewidth=1, color='cyan', alpha=0.8)
            ax1.set_xlabel("Steps")
            ax1.set_ylabel("Program Counter")
            ax1.set_title("Execution Trace")

        # Plot memory usage
        non_zero_addrs = np.nonzero(self.runner.memory)[0]
        if len(non_zero_addrs) > 0:
            values = [int(self.runner.memory[addr]) for addr in non_zero_addrs]
            ax2.scatter(non_zero_addrs, values, c='lime', s=2, alpha=0.7)
            ax2.axvline(x=self.runner.pointer, color='orange', linewidth=2, alpha=0.8)
            ax2.set_xlabel("Memory Address")
            ax2.set_ylabel("Value")
            ax2.set_title("Memory Usage")

        self.figure.tight_layout()
        self.canvas.draw()

    def step_execution(self):
        """Enhanced step execution with better error handling."""
        if not self.runner.program:
            self.runner.load_program(self.code_edit.toPlainText())

        try:
            self.runner.running = True
            continues, old_ptr, new_ptr, mem_addr = self.runner.step()
            self.runner.running = False

            if old_ptr != new_ptr:
                self.update_pointer_highlight(old_ptr, new_ptr)
            if mem_addr != -1:
                self.update_memory_cell(mem_addr)

            self.update_code_highlight()
            self.update_status_info()
            self.update_output_display()

            if self.runner.step_count % 100 == 0:
                self.update_graph()

        except Exception as e:
            QMessageBox.critical(self, "Execution Error", f"Error during execution: {str(e)}")
            self.stop_execution()

    def execute_step(self):
        """Enhanced execution step with performance monitoring and error handling."""
        if not self.runner.running:
            self.timer.stop()
            return

        try:
            current_time = time.time()
            use_jit = self.execution_speed > self.JIT_THRESHOLD

            steps_executed = 0

            if use_jit:
                # High-speed JIT mode
                stop_reason, changed_indices, steps = self.runner.run_jit_step()
                steps_executed = steps

                # Batch update memory cells for performance
                if changed_indices is not None and len(changed_indices) > 0:
                    # Update only visible and important cells
                    important_indices = changed_indices[
                                            (changed_indices >= self.runner.pointer - 50) &
                                            (changed_indices <= self.runner.pointer + 50)
                                            ][:50]  # Limit updates

                    for addr in important_indices:
                        self.update_memory_cell(addr)

                if stop_reason == 3:
                    self.stop_execution()
                    self.status_info.setText("Program finished (JIT mode).")
                    return
                elif stop_reason == 5:
                    self.stop_execution()
                    self.status_info.setText("Execution paused, waiting for input...")
                    return
            else:
                # Single-step mode
                continues, old_ptr, new_ptr, mem_addr = self.runner.step()
                steps_executed = 1

                if old_ptr != new_ptr:
                    self.update_pointer_highlight(old_ptr, new_ptr)
                if mem_addr != -1:
                    self.update_memory_cell(mem_addr)

                if not continues:
                    self.stop_execution()
                    self.status_info.setText("Program finished.")
                    return

            # Update performance counter
            self.performance_counter += steps_executed
            time_diff = current_time - self.last_update_time

            if time_diff >= 1.0:  # Update every second
                steps_per_second = self.performance_counter / time_diff
                self.update_performance_info(steps_per_second)
                self.performance_counter = 0
                self.last_update_time = current_time

            # Update UI components
            self.update_code_highlight()
            self.update_status_info()
            self.update_output_display()

            # Update graph less frequently for better performance
            if self.runner.step_count % (200 if use_jit else 50) == 0:
                self.update_graph()

        except Exception as e:
            QMessageBox.critical(self, "Execution Error", f"Error during execution: {str(e)}")
            self.stop_execution()

    def toggle_execution(self):
        if self.runner.running:
            self.stop_execution()
        else:
            if self.runner.pc >= len(self.runner.program):
                self.reset_execution()

            if not self.runner.program:
                self.runner.load_program(self.code_edit.toPlainText())

            self.runner.running = True
            self.run_button.setText("Pause (F6)")

            # Adaptive timer interval
            if self.execution_speed > self.JIT_THRESHOLD:
                interval = 10  # Fast updates for JIT mode
            else:
                interval = max(1, 1000 // self.execution_speed)

            self.timer.start(interval)
            self.last_update_time = time.time()
            self.performance_counter = 0

    def stop_execution(self):
        self.runner.running = False
        self.timer.stop()
        self.run_button.setText("Run (F6)")
        self.update_performance_info(0)

    def reset_execution(self):
        self.stop_execution()
        self.runner.history = []
        self.update_display_full()
        self.status_info.setText("Ready.")

    def set_speed(self, speed):
        self.execution_speed = speed
        if speed >= 2000:
            self.speed_label.setText("Maximum (JIT)")
        elif speed > self.JIT_THRESHOLD:
            self.speed_label.setText(f"{speed} steps/s (JIT)")
        else:
            self.speed_label.setText(f"{speed} steps/s")

        if self.timer.isActive():
            if speed > self.JIT_THRESHOLD:
                interval = 10
            else:
                interval = max(1, 1000 // speed)
            self.timer.setInterval(interval)

    def update_input_buffer(self):
        text = self.input_line.text()
        self.runner.input_buffer.extend(list(text))
        self.input_line.clear()
        self.update_status_info()
        if not self.runner.running and "waiting for input" in self.status_info.text():
            self.toggle_execution()

    def get_current_instruction(self):
        if self.runner.pc < len(self.runner.program):
            return self.runner.program[self.runner.pc]
        return "End"

    def export_video(self):
        """Enhanced video export with better options."""
        if not CV2_AVAILABLE:
            QMessageBox.critical(self, "Error", "OpenCV library not found. Please run 'pip install opencv-python'.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Save HD Video", "", "MP4 Video (*.mp4)")
        if not path:
            return

        # Create progress dialog
        self.progress_dialog = QProgressDialog("Exporting HD video...", "Cancel", 0, 100, self)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setMinimumDuration(0)

        # Create and start export thread with better settings
        self.export_thread = VideoExportThread(
            self.code_edit.toPlainText(), path,
            fps=60, duration=15  # Higher quality settings
        )
        self.export_thread.progress_update.connect(self.progress_dialog.setValue)
        self.export_thread.status_update.connect(self.progress_dialog.setLabelText)
        self.export_thread.finished_signal.connect(self.on_export_finished)
        self.progress_dialog.canceled.connect(self.export_thread.cancel)

        self.export_thread.start()

    def on_export_finished(self, success, message):
        self.progress_dialog.close()
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.warning(self, "Export Failed", message)
        self.export_thread = None

    def closeEvent(self, event):
        self.stop_execution()
        if self.export_thread:
            self.export_thread.cancel()
            self.export_thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Enhanced dark theme
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ToolTipBase, Qt.white)
    palette.setColor(QPalette.ToolTipText, Qt.white)
    palette.setColor(QPalette.Text, Qt.white)
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.BrightText, Qt.red)
    palette.setColor(QPalette.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    window = BrainFuckVisualizer()
    window.show()
    sys.exit(app.exec_())