from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

from PyQt6.QtCore import QSettings, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.validators import validate_generation_inputs


PROJECT_ROOT = Path(__file__).resolve().parent.parent

APP_STYLE = """
QWidget {
    background: #171b22;
    color: #e7e0d3;
    font-family: "Segoe UI", "Bahnschrift";
    font-size: 13px;
}
QMainWindow {
    background: #171b22;
}
QWidget#central_shell {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #171b22, stop:0.55 #161a21, stop:1 #1a2028);
}
QWidget#hero_panel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1a2028, stop:0.4 #1d232d, stop:1 #131820);
    border: 1px solid #2f3947;
    border-radius: 18px;
}
QWidget#hero_meta {
    background: transparent;
}
QWidget#right_shell, QWidget#left_shell {
    background: transparent;
}
QWidget#button_band {
    background: transparent;
}
QWidget#console_card {
    background: #1b2028;
    border: 1px solid #313c4b;
    border-radius: 16px;
}
QWidget#output_card {
    background: #1a2028;
    border: 1px solid #313c4b;
    border-radius: 16px;
}
QWidget#metric_chip {
    background: #222935;
    border: 1px solid #364356;
    border-radius: 13px;
}
QLabel#metric_kicker {
    color: #7e91a8;
    font-size: 11px;
    letter-spacing: 1px;
    text-transform: uppercase;
}
QLabel#metric_value {
    color: #e8decb;
    font-size: 13px;
    font-weight: 600;
}
QLabel#hero_eyebrow {
    color: #8fb6cf;
    font-size: 11px;
    letter-spacing: 3px;
    text-transform: uppercase;
}
QLabel#hero_title {
    color: #f2ecdf;
    font-family: "Bahnschrift SemiCondensed", "Segoe UI Semibold";
    font-size: 29px;
    font-weight: 600;
    letter-spacing: 1px;
}
QLabel#hero_subtitle {
    color: #96a5b8;
    font-size: 13px;
    line-height: 1.5;
}
QLabel#section_kicker {
    color: #7e91a8;
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
}
QLabel#section_title {
    color: #f1eadf;
    font-family: "Bahnschrift SemiCondensed", "Segoe UI Semibold";
    font-size: 18px;
    font-weight: 600;
}
QLabel#section_note {
    color: #8a98a8;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: #12161d;
    width: 12px;
    margin: 4px 0 4px 0;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #3a4556;
    min-height: 28px;
    border-radius: 6px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
QGroupBox {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1b2028, stop:1 #171c24);
    border: 1px solid #313c4b;
    border-radius: 16px;
    margin-top: 14px;
    padding-top: 18px;
    padding-left: 4px;
    padding-right: 4px;
    padding-bottom: 6px;
    font-weight: 600;
    color: #b7c6d6;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    padding: 0 8px 0 8px;
    color: #9cb6c9;
    background: #1b2028;
}
QLabel {
    background: transparent;
}
QLabel[hint="true"] {
    color: #8292a3;
}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit {
    background: #20252e;
    border: 1px solid #394453;
    border-radius: 10px;
    padding: 7px 10px;
    selection-background-color: #587d95;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus {
    border: 1px solid #7ca4bc;
    background: #232a34;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    width: 10px;
    height: 10px;
    border-left: 1px solid #8da2b5;
    border-bottom: 1px solid #8da2b5;
    margin-right: 10px;
    transform: rotate(-45deg);
}
QCheckBox {
    spacing: 8px;
    color: #d9d1c4;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid #465264;
    background: #21262f;
}
QCheckBox::indicator:checked {
    background: #6f8fa3;
    border: 1px solid #87aabd;
}
QPushButton {
    background: #28303a;
    border: 1px solid #425063;
    border-radius: 12px;
    padding: 10px 16px;
    color: #ece4d6;
    font-weight: 600;
}
QPushButton:hover {
    background: #313b48;
    border-color: #577089;
}
QPushButton:pressed {
    background: #212832;
}
QPushButton#generate_button {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #5b7b8d, stop:1 #6c95a9);
    border-color: #7aa6bb;
    color: #f7f3ee;
    font-weight: 700;
    padding: 14px 22px;
}
QPushButton#ai_button {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #635286, stop:1 #7b66a3);
    border-color: #8b76b4;
    color: #f7f3ee;
    font-weight: 700;
}
QPushButton#ghost_button {
    background: #21262f;
    border: 1px solid #425063;
    color: #d8d0c2;
    font-weight: 600;
}
QTextEdit#log_panel {
    font-family: Consolas, "Cascadia Mono";
    background: #11151b;
    color: #a6d0b7;
    border-radius: 12px;
    border: 1px solid #313c4b;
}
QTextEdit#ai_panel {
    background: #12151d;
    color: #e3dcf5;
    border-radius: 12px;
    border: 1px solid #313c4b;
}
QTabWidget::pane {
    border: 1px solid #313c4b;
    border-radius: 14px;
    background: #171c24;
    top: -1px;
}
QTabBar::tab {
    background: #222832;
    color: #8e9cac;
    border: 1px solid #364354;
    border-bottom: none;
    padding: 8px 14px;
    margin-right: 4px;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
}
QTabBar::tab:selected {
    background: #f0e5d4;
    color: #3a424f;
    border-color: #f0e5d4;
}
QTabBar::tab:hover:!selected {
    color: #d9d1c4;
}
QProgressBar {
    border: 1px solid #313c4b;
    border-radius: 10px;
    background: #20252d;
    color: #d4cdc2;
    text-align: center;
    min-height: 14px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6d8da0, stop:1 #87adbf);
    border-radius: 8px;
}
QSplitter::handle {
    background: #20252d;
    width: 8px;
}
QSplitter::handle:hover {
    background: #314052;
}
"""


class GeneratorWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)

    def __init__(self, raw_params: dict, blender_path: str):
        super().__init__()
        self.raw_params = raw_params
        self.blender_path = blender_path

    def run(self) -> None:
        from app.controller import run_generation

        result = run_generation(
            self.raw_params,
            self.blender_path,
            progress_callback=lambda message: self.progress.emit(message),
        )
        self.finished.emit(result)


class AIWorker(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(object)

    def __init__(
        self,
        brief: str,
        current_params: dict,
        provider: str,
        goal: str,
        model: str,
        openai_api_key: str,
        gemini_api_key: str,
    ):
        super().__init__()
        self.brief = brief
        self.current_params = current_params
        self.provider = provider
        self.goal = goal
        self.model = model
        self.openai_api_key = openai_api_key
        self.gemini_api_key = gemini_api_key

    def run(self) -> None:
        try:
            from ai.service import generate_house_plan

            self.progress.emit(f"Sending brief to {self.provider}...")
            result = generate_house_plan(
                self.brief,
                self.current_params,
                provider=self.provider,
                goal=self.goal,
                model=self.model,
                openai_api_key=self.openai_api_key,
                gemini_api_key=self.gemini_api_key,
            )
        except Exception as exc:
            result = SimpleNamespace(
                success=False,
                message=(
                    "AI layer is unavailable.\n"
                    f"{exc}\n\n"
                    "Install the project requirements into the active interpreter and try again."
                ),
                parsed=None,
                gui_parameters={},
                technical_instruction="",
            )
        self.finished.emit(result)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings("ArchGen", "ZeroTemplateGenerator")
        self.worker: Optional[GeneratorWorker] = None
        self.ai_worker: Optional[AIWorker] = None
        self._blend_path = ""
        self._active_ai_payload: Optional[dict] = None

        self.setWindowTitle("Zero-Template House Generator")
        self.resize(1320, 900)
        self.setMinimumSize(1180, 780)
        self.setStyleSheet(APP_STYLE)

        self._build_ui()
        self._restore_settings()

    def _build_ui(self) -> None:
        root_widget = QWidget()
        root_widget.setObjectName("central_shell")
        self.setCentralWidget(root_widget)
        root_layout = QVBoxLayout(root_widget)
        root_layout.setContentsMargins(18, 18, 18, 18)
        root_layout.setSpacing(14)

        root_layout.addWidget(self._build_header())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        params_holder = QWidget()
        params_holder.setObjectName("left_shell")
        self.params_layout = QVBoxLayout(params_holder)
        self.params_layout.setContentsMargins(0, 0, 8, 0)
        self.params_layout.setSpacing(12)

        self._build_ai_section()
        self._build_blender_section()
        self._build_massing_section()
        self._build_roof_section()
        self._build_facade_section()
        self._build_entrance_section()
        self._build_volumes_section()
        self._build_style_section()
        self._build_notes_section()
        self.params_layout.addStretch(1)

        scroll.setWidget(params_holder)
        splitter.addWidget(scroll)
        splitter.addWidget(self._build_right_panel())
        splitter.setSizes([720, 560])

        root_layout.addWidget(splitter)

    def _build_header(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("hero_panel")
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(18)

        copy_col = QVBoxLayout()
        copy_col.setSpacing(6)
        eyebrow = QLabel("Architectural Synthesis Platform")
        eyebrow.setObjectName("hero_eyebrow")
        title = QLabel("Zero-Template House Generator")
        title.setObjectName("hero_title")
        subtitle = QLabel(
            "Prompt-driven residential massing, facade logic, Blender 5.1 generation and compliance in one desktop pipeline."
        )
        subtitle.setObjectName("hero_subtitle")
        subtitle.setWordWrap(True)
        copy_col.addWidget(eyebrow)
        copy_col.addWidget(title)
        copy_col.addWidget(subtitle)

        meta_col = QVBoxLayout()
        meta_col.setObjectName("hero_meta")
        meta_col.setSpacing(10)
        meta_col.addWidget(self._make_metric_chip("Mode", "Prompt-only + Zero-template"))
        meta_col.addWidget(self._make_metric_chip("Pipeline", "GUI → AI → Resolve → Blender"))
        meta_col.addWidget(self._make_metric_chip("Current Scope", "Phase A + AI brief interpreter"))

        layout.addLayout(copy_col, 1)
        layout.addStretch(1)
        layout.addLayout(meta_col)
        return widget

    def _make_metric_chip(self, kicker: str, value: str) -> QWidget:
        chip = QWidget()
        chip.setObjectName("metric_chip")
        layout = QVBoxLayout(chip)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)
        kicker_label = QLabel(kicker)
        kicker_label.setObjectName("metric_kicker")
        value_label = QLabel(value)
        value_label.setObjectName("metric_value")
        value_label.setWordWrap(True)
        layout.addWidget(kicker_label)
        layout.addWidget(value_label)
        return chip

    def _build_right_panel(self) -> QWidget:
        widget = QWidget()
        widget.setObjectName("right_shell")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(12)

        heading = QWidget()
        heading_layout = QVBoxLayout(heading)
        heading_layout.setContentsMargins(0, 0, 0, 0)
        heading_layout.setSpacing(2)
        kicker = QLabel("Generation Console")
        kicker.setObjectName("section_kicker")
        title = QLabel("Control Room")
        title.setObjectName("section_title")
        note = QLabel("Run AI interpretation, inspect the plan, then launch Blender generation and verification.")
        note.setObjectName("section_note")
        note.setWordWrap(True)
        heading_layout.addWidget(kicker)
        heading_layout.addWidget(title)
        heading_layout.addWidget(note)
        layout.addWidget(heading)

        button_row = QWidget()
        button_row.setObjectName("button_band")
        button_layout = QHBoxLayout(button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)

        self.ai_button = QPushButton("AI Analyze Brief")
        self.ai_button.setObjectName("ai_button")
        self.ai_button.clicked.connect(self._on_ai_generate)
        button_layout.addWidget(self.ai_button)

        self.generate_button = QPushButton("Generate Scene")
        self.generate_button.setObjectName("generate_button")
        self.generate_button.clicked.connect(self._on_generate)
        button_layout.addWidget(self.generate_button)
        layout.addWidget(button_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        console_card = QWidget()
        console_card.setObjectName("console_card")
        console_layout = QVBoxLayout(console_card)
        console_layout.setContentsMargins(14, 14, 14, 14)
        console_layout.setSpacing(10)

        self.tabs = QTabWidget()
        self.log_panel = QTextEdit()
        self.log_panel.setObjectName("log_panel")
        self.log_panel.setReadOnly(True)
        self.tabs.addTab(self.log_panel, "Runtime Log")

        self.ai_output_panel = QTextEdit()
        self.ai_output_panel.setObjectName("ai_panel")
        self.ai_output_panel.setReadOnly(True)
        self.tabs.addTab(self.ai_output_panel, "AI Plan")
        console_layout.addWidget(self.tabs, 1)
        layout.addWidget(console_card, 1)

        output_group = QGroupBox("Output")
        output_group.setObjectName("output_card")
        output_layout = QHBoxLayout(output_group)
        output_layout.setSpacing(10)
        self.open_blend_button = QPushButton("Open .blend")
        self.open_blend_button.setObjectName("ghost_button")
        self.open_blend_button.setEnabled(False)
        self.open_blend_button.clicked.connect(self._open_blend)
        open_folder_button = QPushButton("Open Output Folder")
        open_folder_button.setObjectName("ghost_button")
        open_folder_button.clicked.connect(self._open_output_folder)
        output_layout.addWidget(self.open_blend_button)
        output_layout.addWidget(open_folder_button)
        output_layout.addStretch(1)
        layout.addWidget(output_group)
        return widget

    def _build_ai_section(self) -> None:
        group = QGroupBox("AI Design Interpreter")
        layout = QVBoxLayout(group)

        top_grid = QGridLayout()
        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItems(["openai", "gemini"])
        self.ai_provider_combo.currentTextChanged.connect(self._on_ai_provider_changed)

        self.ai_goal_combo = QComboBox()
        self.ai_goal_combo.addItems(["design_and_gui", "space_program"])

        self.ai_model_combo = QComboBox()
        self.openai_api_key_edit = QLineEdit()
        self.openai_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_api_key_edit.setPlaceholderText("Session-only OpenAI key or use OPENAI_API_KEY.")
        self.gemini_api_key_edit = QLineEdit()
        self.gemini_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_api_key_edit.setPlaceholderText("Session-only Gemini key or use GEMINI_API_KEY.")

        top_grid.addWidget(QLabel("Provider"), 0, 0)
        top_grid.addWidget(self.ai_provider_combo, 0, 1)
        top_grid.addWidget(QLabel("Goal"), 0, 2)
        top_grid.addWidget(self.ai_goal_combo, 0, 3)
        top_grid.addWidget(QLabel("Model"), 1, 0)
        top_grid.addWidget(self.ai_model_combo, 1, 1)
        top_grid.addWidget(QLabel("OpenAI API Key"), 2, 0)
        top_grid.addWidget(self.openai_api_key_edit, 2, 1, 1, 3)
        top_grid.addWidget(QLabel("Gemini API Key"), 3, 0)
        top_grid.addWidget(self.gemini_api_key_edit, 3, 1, 1, 3)
        layout.addLayout(top_grid)

        self.ai_brief_edit = QTextEdit()
        self.ai_brief_edit.setFixedHeight(120)
        self.ai_brief_edit.setPlaceholderText(
            "Describe the house in natural language. Example: modern two-floor family house, 4 bedrooms, no columns, terrace, hip roof, warm stucco facade, unique composition."
        )
        layout.addWidget(self.ai_brief_edit)

        note = QLabel(
            "AI fills only real GUI controls, writes a technical planning brief, and saves a formal space program. "
            "Prompt-only mode is active: the current brief overrides old GUI state, and optional features are not added unless requested. "
            "API keys are session-only and are not stored in settings. "
            "If a typed key is wrong, clear the field to use GEMINI_API_KEY / OPENAI_API_KEY from the environment."
        )
        note.setStyleSheet("color: #7d8793;")
        note.setWordWrap(True)
        layout.addWidget(note)
        self.params_layout.addWidget(group)

    def _build_blender_section(self) -> None:
        group = QGroupBox("Blender")
        layout = QHBoxLayout(group)
        self.blender_path_edit = QLineEdit()
        self.blender_path_edit.setPlaceholderText("Select blender.exe")
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse_blender)
        validate_button = QPushButton("Validate")
        validate_button.clicked.connect(self._validate_blender)
        layout.addWidget(self.blender_path_edit, 1)
        layout.addWidget(browse_button)
        layout.addWidget(validate_button)
        self.params_layout.addWidget(group)

    def _build_massing_section(self) -> None:
        group = QGroupBox("Massing")
        grid = QGridLayout(group)
        self.width_spin = self._make_double_spin(6.0, 60.0, 14.0, 0.5, "m")
        self.depth_spin = self._make_double_spin(6.0, 45.0, 11.0, 0.5, "m")
        self.floors_spin = self._make_spin(1, 5, 2)
        self.floors_spin.valueChanged.connect(self._on_floors_changed)
        self.floor_height_spin = self._make_double_spin(2.6, 4.8, 3.2, 0.1, "m")
        grid.addWidget(QLabel("Width"), 0, 0)
        grid.addWidget(self.width_spin, 0, 1)
        grid.addWidget(QLabel("Depth"), 0, 2)
        grid.addWidget(self.depth_spin, 0, 3)
        grid.addWidget(QLabel("Floors"), 1, 0)
        grid.addWidget(self.floors_spin, 1, 1)
        grid.addWidget(QLabel("Floor Height"), 1, 2)
        grid.addWidget(self.floor_height_spin, 1, 3)
        self.params_layout.addWidget(group)

    def _build_roof_section(self) -> None:
        group = QGroupBox("Roof")
        grid = QGridLayout(group)
        self.roof_type_combo = QComboBox()
        self.roof_type_combo.addItems(["gable", "hip", "flat"])
        self.roof_type_combo.currentTextChanged.connect(self._on_roof_type_changed)
        self.roof_pitch_spin = self._make_double_spin(10.0, 55.0, 28.0, 1.0, "deg")
        grid.addWidget(QLabel("Roof Type"), 0, 0)
        grid.addWidget(self.roof_type_combo, 0, 1)
        grid.addWidget(QLabel("Pitch"), 0, 2)
        grid.addWidget(self.roof_pitch_spin, 0, 3)
        self.params_layout.addWidget(group)

    def _build_facade_section(self) -> None:
        group = QGroupBox("Facade Grid And Openings")
        grid = QGridLayout(group)
        self.window_count_spin = self._make_spin(0, 9, 0)
        self.window_count_spin.setToolTip(
            "Manual target for front windows per upper facade. 0 = automatic."
        )
        self.window_style_combo = QComboBox()
        self.window_style_combo.addItems(["modern", "classic", "square"])
        self.wall_material_combo = QComboBox()
        self.wall_material_combo.addItems(["stucco", "brick", "stone", "concrete", "siding", "log_wood"])
        note = QLabel("0 keeps front window rhythm automatic. Single-floor manual counts must be even.")
        note.setWordWrap(True)
        note.setStyleSheet("color: #7d8793;")
        grid.addWidget(QLabel("Front Windows"), 0, 0)
        grid.addWidget(self.window_count_spin, 0, 1)
        grid.addWidget(QLabel("Window Style"), 1, 0)
        grid.addWidget(self.window_style_combo, 1, 1)
        grid.addWidget(QLabel("Wall Material"), 1, 2)
        grid.addWidget(self.wall_material_combo, 1, 3)
        grid.addWidget(note, 2, 0, 1, 4)
        self.params_layout.addWidget(group)

    def _build_entrance_section(self) -> None:
        group = QGroupBox("Entrance")
        grid = QGridLayout(group)
        self.entrance_style_combo = QComboBox()
        self.entrance_style_combo.addItems(["modern", "classic"])
        self.columns_check = QCheckBox("Columns")
        self.pediment_check = QCheckBox("Pediment")
        self.portico_check = QCheckBox("Portico")
        grid.addWidget(QLabel("Entrance Style"), 0, 0)
        grid.addWidget(self.entrance_style_combo, 0, 1)
        grid.addWidget(self.columns_check, 1, 0)
        grid.addWidget(self.pediment_check, 1, 1)
        grid.addWidget(self.portico_check, 1, 2)
        self.params_layout.addWidget(group)

    def _build_volumes_section(self) -> None:
        group = QGroupBox("Optional Volumes")
        grid = QGridLayout(group)
        self.garage_check = QCheckBox("Attached Garage")
        self.terrace_check = QCheckBox("Front Terrace")
        self.balcony_check = QCheckBox("Balcony")
        self.fence_check = QCheckBox("Fence")
        grid.addWidget(self.garage_check, 0, 0)
        grid.addWidget(self.terrace_check, 0, 1)
        grid.addWidget(self.balcony_check, 1, 0)
        grid.addWidget(self.fence_check, 1, 1)
        self.params_layout.addWidget(group)

    def _build_style_section(self) -> None:
        group = QGroupBox("Architectural Style")
        layout = QVBoxLayout(group)
        self.arch_style_combo = QComboBox()
        self.arch_style_combo.addItems(
            ["modern_villa", "grand_estate", "classic_luxury_mansion", "scandinavian_barnhouse", "traditional_suburban", "rustic_log_cabin"]
        )
        description = QLabel(
            "Style affects facade proportions, opening rhythm, wall thickness, roof overhang and entrance sizing."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #7d8793;")
        layout.addWidget(self.arch_style_combo)
        layout.addWidget(description)
        self.params_layout.addWidget(group)

    def _build_notes_section(self) -> None:
        group = QGroupBox("Special Notes")
        layout = QVBoxLayout(group)
        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(84)
        self.notes_edit.setPlaceholderText(
            "Examples: no columns, flat roof, без колонн, убрать забор, add garage"
        )
        note = QLabel("Notes already override RU/EN boolean toggles and roof type when detected.")
        note.setStyleSheet("color: #7d8793;")
        note.setWordWrap(True)
        layout.addWidget(self.notes_edit)
        layout.addWidget(note)
        self.params_layout.addWidget(group)

    def _make_spin(self, minimum: int, maximum: int, value: int) -> QSpinBox:
        spin = QSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        return spin

    def _make_double_spin(
        self,
        minimum: float,
        maximum: float,
        value: float,
        step: float,
        suffix: str = "",
    ) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSingleStep(step)
        spin.setDecimals(2 if step < 0.1 else 1)
        if suffix:
            spin.setSuffix(f" {suffix}")
        return spin

    def _collect_params(self) -> dict:
        return {
            "width": self.width_spin.value(),
            "depth": self.depth_spin.value(),
            "floors": self.floors_spin.value(),
            "floor_height": self.floor_height_spin.value(),
            "roof_type": self.roof_type_combo.currentText(),
            "roof_pitch": self.roof_pitch_spin.value(),
            "window_count_front": self.window_count_spin.value(),
            "window_style": self.window_style_combo.currentText(),
            "wall_material": self.wall_material_combo.currentText(),
            "entrance_style": self.entrance_style_combo.currentText(),
            "has_columns": self.columns_check.isChecked(),
            "has_pediment": self.pediment_check.isChecked(),
            "has_portico": self.portico_check.isChecked(),
            "has_garage": self.garage_check.isChecked(),
            "has_terrace": self.terrace_check.isChecked(),
            "has_balcony": self.balcony_check.isChecked(),
            "has_fence": self.fence_check.isChecked(),
            "arch_style": self.arch_style_combo.currentText(),
            "special_notes": self.notes_edit.toPlainText().strip(),
        }

    def _apply_params(self, params: dict) -> None:
        self.width_spin.setValue(float(params.get("width", self.width_spin.value())))
        self.depth_spin.setValue(float(params.get("depth", self.depth_spin.value())))
        self.floors_spin.setValue(int(params.get("floors", self.floors_spin.value())))
        self.floor_height_spin.setValue(float(params.get("floor_height", self.floor_height_spin.value())))
        self.roof_type_combo.setCurrentText(str(params.get("roof_type", self.roof_type_combo.currentText())))
        self.roof_pitch_spin.setValue(float(params.get("roof_pitch", self.roof_pitch_spin.value())))
        self.window_count_spin.setValue(int(params.get("window_count_front", self.window_count_spin.value())))
        self.window_style_combo.setCurrentText(str(params.get("window_style", self.window_style_combo.currentText())))
        self.wall_material_combo.setCurrentText(str(params.get("wall_material", self.wall_material_combo.currentText())))
        self.entrance_style_combo.setCurrentText(str(params.get("entrance_style", self.entrance_style_combo.currentText())))
        self.columns_check.setChecked(bool(params.get("has_columns", self.columns_check.isChecked())))
        self.pediment_check.setChecked(bool(params.get("has_pediment", self.pediment_check.isChecked())))
        self.portico_check.setChecked(bool(params.get("has_portico", self.portico_check.isChecked())))
        self.garage_check.setChecked(bool(params.get("has_garage", self.garage_check.isChecked())))
        self.terrace_check.setChecked(bool(params.get("has_terrace", self.terrace_check.isChecked())))
        self.balcony_check.setChecked(bool(params.get("has_balcony", self.balcony_check.isChecked())))
        self.fence_check.setChecked(bool(params.get("has_fence", self.fence_check.isChecked())))
        self.arch_style_combo.setCurrentText(str(params.get("arch_style", self.arch_style_combo.currentText())))
        self.notes_edit.setPlainText(str(params.get("special_notes", self.notes_edit.toPlainText())))
        self._on_roof_type_changed(self.roof_type_combo.currentText())
        self._on_floors_changed(self.floors_spin.value())

    def _on_ai_generate(self) -> None:
        brief = self.ai_brief_edit.toPlainText().strip()
        if not brief:
            QMessageBox.warning(self, "Missing AI Brief", "Describe the house brief for AI first.")
            return

        self._save_settings()
        self._set_busy(True)
        self._log("Starting AI brief interpretation...")
        self.tabs.setCurrentWidget(self.ai_output_panel)
        self.ai_output_panel.clear()

        self.ai_worker = AIWorker(
            brief=brief,
            current_params=self._collect_params(),
            provider=self.ai_provider_combo.currentText(),
            goal=self.ai_goal_combo.currentText(),
            model=self.ai_model_combo.currentText(),
            openai_api_key=self.openai_api_key_edit.text().strip(),
            gemini_api_key=self.gemini_api_key_edit.text().strip(),
        )
        self.ai_worker.progress.connect(self._log)
        self.ai_worker.finished.connect(self._on_ai_finished)
        self.ai_worker.start()

    def _on_ai_finished(self, result) -> None:
        self._set_busy(False)
        if not result.success:
            self._log(result.message)
            QMessageBox.critical(self, "AI Brief Failed", result.message)
            return

        self._active_ai_payload = result.parsed if isinstance(result.parsed, dict) else None
        self._apply_params(result.gui_parameters)
        self.ai_output_panel.setPlainText(result.technical_instruction)
        self.tabs.setCurrentWidget(self.ai_output_panel)
        self._log(result.message)
        if result.parsed:
            concept = result.parsed.get("architectural_concept", "")
            if concept:
                self._log(f"AI concept: {concept}")
            space_program = result.parsed.get("space_program", {})
            if space_program:
                self._log(
                    f"AI space program rooms: {len(space_program.get('room_program', []))}"
                )
            notes = result.parsed.get("constraint_notes", [])
            for note in notes:
                self._log(f"AI note: {note}")
        QMessageBox.information(self, "AI Brief Ready", result.message)

    def _on_generate(self) -> None:
        blender_path = self.blender_path_edit.text().strip()
        if not blender_path:
            QMessageBox.warning(self, "Missing Blender Path", "Select a Blender executable first.")
            return

        params = self._collect_params()
        if self._active_ai_payload:
            params["ai_design_payload"] = self._active_ai_payload
        errors = validate_generation_inputs(params)
        if errors:
            QMessageBox.critical(self, "Invalid Parameters", "\n".join(errors))
            return

        self._save_settings()
        self._set_busy(True)
        self._blend_path = ""
        self.open_blend_button.setEnabled(False)
        self.log_panel.clear()
        self.tabs.setCurrentWidget(self.log_panel)
        self._log("Raw GUI input:")
        self._log(json.dumps(params, indent=2, ensure_ascii=False))

        self.worker = GeneratorWorker(params, blender_path)
        self.worker.progress.connect(self._log)
        self.worker.finished.connect(self._on_generation_finished)
        self.worker.start()

    def _on_generation_finished(self, result) -> None:
        self._set_busy(False)

        if result.parse_notes:
            self._log("Detected note overrides:")
            for note in result.parse_notes:
                self._log(f"- {note}")

        if result.success:
            self._blend_path = result.blend_path
            self.open_blend_button.setEnabled(bool(result.blend_path))
            self._log(result.message)
            QMessageBox.information(self, "Generation Complete", result.message)
        else:
            self._log(result.message)
            if result.stderr:
                self._log("Blender stderr tail:")
                self._log(result.stderr[-1800:])
            QMessageBox.critical(self, "Generation Failed", result.message)

        if result.violations:
            self._log("Compliance violations:")
            for violation in result.violations:
                self._log(f"- {violation}")

    def _set_busy(self, state: bool) -> None:
        self.generate_button.setEnabled(not state)
        self.ai_button.setEnabled(not state)
        self.progress_bar.setVisible(state)

    def _log(self, message: str) -> None:
        self.log_panel.append(message.rstrip())

    def _browse_blender(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Blender Executable",
            "",
            "Executables (*.exe);;All files (*)",
        )
        if file_path:
            self.blender_path_edit.setText(file_path)

    def _validate_blender(self) -> None:
        from app.controller import validate_blender_path

        valid, message = validate_blender_path(self.blender_path_edit.text().strip())
        if valid:
            QMessageBox.information(self, "Blender Validated", message)
        else:
            QMessageBox.critical(self, "Blender Invalid", message)

    def _on_roof_type_changed(self, roof_type: str) -> None:
        self.roof_pitch_spin.setEnabled(roof_type != "flat")

    def _on_ai_provider_changed(self, provider: str) -> None:
        self.ai_model_combo.clear()
        if provider == "gemini":
            self.ai_model_combo.addItems(["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite"])
        else:
            self.ai_model_combo.addItems(["gpt-5.4-mini", "gpt-5.4", "gpt-5-mini"])

    def _on_floors_changed(self, floors: int) -> None:
        if floors < 2:
            self.balcony_check.setChecked(False)
        self.balcony_check.setEnabled(floors >= 2)

    def _open_blend(self) -> None:
        if not self._blend_path:
            return
        self._open_path(Path(self._blend_path))

    def _open_output_folder(self) -> None:
        output_dir = PROJECT_ROOT / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        self._open_path(output_dir)

    def _open_path(self, path: Path) -> None:
        if os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
            return
        subprocess.Popen(["xdg-open", str(path)])

    def _save_settings(self) -> None:
        settings = self.settings
        settings.setValue("blender_path", self.blender_path_edit.text())
        settings.setValue("ai_provider", self.ai_provider_combo.currentText())
        settings.setValue("ai_model", self.ai_model_combo.currentText())
        settings.setValue("ai_goal", self.ai_goal_combo.currentText())
        settings.setValue("ai_brief", self.ai_brief_edit.toPlainText())
        for key, value in self._collect_params().items():
            settings.setValue(key, value)

    def _restore_settings(self) -> None:
        settings = self.settings
        self.blender_path_edit.setText(settings.value("blender_path", ""))
        self.ai_provider_combo.setCurrentText(str(settings.value("ai_provider", "openai")))
        self._on_ai_provider_changed(self.ai_provider_combo.currentText())
        self.ai_model_combo.setCurrentText(str(settings.value("ai_model", self.ai_model_combo.currentText())))
        self.ai_goal_combo.setCurrentText(str(settings.value("ai_goal", "design_and_gui")))
        self.ai_brief_edit.setPlainText(str(settings.value("ai_brief", "")))
        self.width_spin.setValue(float(settings.value("width", 14.0)))
        self.depth_spin.setValue(float(settings.value("depth", 11.0)))
        self.floors_spin.setValue(int(settings.value("floors", 2)))
        self.floor_height_spin.setValue(float(settings.value("floor_height", 3.2)))
        self.roof_type_combo.setCurrentText(str(settings.value("roof_type", "hip")))
        self.roof_pitch_spin.setValue(float(settings.value("roof_pitch", 28.0)))
        self.window_count_spin.setValue(int(settings.value("window_count_front", 0)))
        self.window_style_combo.setCurrentText(str(settings.value("window_style", "modern")))
        self.wall_material_combo.setCurrentText(str(settings.value("wall_material", "stucco")))
        self.entrance_style_combo.setCurrentText(str(settings.value("entrance_style", "modern")))
        self.columns_check.setChecked(str(settings.value("has_columns", "false")).lower() == "true")
        self.pediment_check.setChecked(str(settings.value("has_pediment", "false")).lower() == "true")
        self.portico_check.setChecked(str(settings.value("has_portico", "false")).lower() == "true")
        self.garage_check.setChecked(str(settings.value("has_garage", "false")).lower() == "true")
        self.terrace_check.setChecked(str(settings.value("has_terrace", "false")).lower() == "true")
        self.balcony_check.setChecked(str(settings.value("has_balcony", "false")).lower() == "true")
        self.fence_check.setChecked(str(settings.value("has_fence", "false")).lower() == "true")
        self.arch_style_combo.setCurrentText(str(settings.value("arch_style", "modern_villa")))
        self.notes_edit.setPlainText(str(settings.value("special_notes", "")))
        self._on_roof_type_changed(self.roof_type_combo.currentText())
        self._on_floors_changed(self.floors_spin.value())
