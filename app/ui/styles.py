"""Modern Dark UI Theme for AI Dubbing Studio"""

DARK_THEME = """
QWidget {
    background-color: #1a1b26;
    color: #c0caf5;
    font-family: 'Segoe UI', 'San Francisco', Arial, sans-serif;
    font-size: 13px;
    selection-background-color: #3d59a1;
    selection-color: #ffffff;
}

/* Sidebar navigation */
QFrame#Sidebar {
    background-color: #16161e;
    border-right: 1px solid #292e42;
    min-width: 210px;
    max-width: 230px;
}

QPushButton#NavButton {
    background-color: transparent;
    color: #a9b1d6;
    text-align: left;
    padding: 12px 16px;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 500;
}

QPushButton#NavButton:hover {
    background-color: #24283b;
    color: #7aa2f7;
}

QPushButton#NavButton:checked {
    background-color: #2e3c64;
    color: #7aa2f7;
    font-weight: bold;
    border-left: 4px solid #7aa2f7;
}

/* Standard Buttons */
QPushButton {
    background-color: #24283b;
    color: #c0caf5;
    border: 1px solid #3b4261;
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 500;
}

QPushButton:hover {
    background-color: #2f354f;
    border-color: #7aa2f7;
}

QPushButton:pressed {
    background-color: #1f2335;
}

QPushButton:disabled {
    background-color: #1f2335;
    color: #565f89;
    border-color: #292e42;
}

QPushButton#PrimaryButton {
    background-color: #7aa2f7;
    color: #15161e;
    font-weight: bold;
    border: none;
}

QPushButton#PrimaryButton:hover {
    background-color: #89b4fa;
}

QPushButton#PrimaryButton:pressed {
    background-color: #5d87e0;
}

QPushButton#DangerButton {
    background-color: #f7768e;
    color: #15161e;
    font-weight: bold;
    border: none;
}

QPushButton#DangerButton:hover {
    background-color: #ff8b9e;
}

/* Form inputs & controls */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #1f2335;
    color: #c0caf5;
    border: 1px solid #292e42;
    border-radius: 6px;
    padding: 6px 10px;
}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #7aa2f7;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #1f2335;
    border: 1px solid #3b4261;
    selection-background-color: #3d59a1;
}

/* Tables */
QTableWidget {
    background-color: #1f2335;
    border: 1px solid #292e42;
    gridline-color: #292e42;
    border-radius: 6px;
}

QTableWidget::item {
    padding: 6px;
    border-bottom: 1px solid #24283b;
}

QTableWidget::item:selected {
    background-color: #2e3c64;
    color: #ffffff;
}

QHeaderView::section {
    background-color: #16161e;
    color: #7aa2f7;
    font-weight: bold;
    padding: 8px;
    border: 1px solid #292e42;
}

/* Progress bar */
QProgressBar {
    background-color: #1f2335;
    border: 1px solid #292e42;
    border-radius: 6px;
    text-align: center;
    color: #ffffff;
    font-weight: bold;
    height: 18px;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7aa2f7, stop:1 #bb9af7);
    border-radius: 5px;
}

/* Sliders */
QSlider::groove:horizontal {
    height: 6px;
    background: #24283b;
    border-radius: 3px;
}

QSlider::sub-page:horizontal {
    background: #7aa2f7;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    background: #c0caf5;
    border: 2px solid #7aa2f7;
    width: 14px;
    margin-top: -4px;
    margin-bottom: -4px;
    border-radius: 7px;
}

/* GroupBox & Frames */
QGroupBox {
    border: 1px solid #292e42;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 16px;
    font-weight: bold;
    color: #7aa2f7;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px;
    padding: 0 4px;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #1a1b26;
    width: 10px;
    border-radius: 5px;
}

QScrollBar::handle:vertical {
    background: #292e42;
    min-height: 20px;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background: #3b4261;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""

