"""
Modern styling for the ShareLink Extractor application.
"""

DARK_THEME = """
QMainWindow {
    background-color: #1a1a2e;
}

QWidget {
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #e0e0e0;
}

QLabel {
    color: #e0e0e0;
}

QLabel#titleLabel {
    font-size: 24px;
    font-weight: bold;
    color: #00d9ff;
    padding: 10px;
}

QLabel#subtitleLabel {
    font-size: 14px;
    color: #888;
    padding-bottom: 20px;
}

QLabel#sectionLabel {
    font-size: 15px;
    font-weight: bold;
    color: #00d9ff;
    padding: 5px 0;
}

QTextEdit {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 8px;
    padding: 12px;
    font-size: 13px;
    color: #e0e0e0;
    selection-background-color: #00d9ff;
    selection-color: #1a1a2e;
}

QTextEdit:focus {
    border-color: #00d9ff;
}

QTextEdit#inputArea {
    min-height: 120px;
}

QTextEdit#outputArea {
    background-color: #0f3460;
    min-height: 200px;
}

QPushButton {
    background-color: #0f3460;
    border: 2px solid #00d9ff;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 14px;
    font-weight: bold;
    color: #00d9ff;
    min-width: 120px;
}

QPushButton:hover {
    background-color: #00d9ff;
    color: #1a1a2e;
}

QPushButton:pressed {
    background-color: #00b8d4;
}

QPushButton:disabled {
    background-color: #2a2a3e;
    border-color: #444;
    color: #666;
}

QPushButton#primaryButton {
    background-color: #00d9ff;
    color: #1a1a2e;
    font-size: 16px;
    padding: 14px 32px;
}

QPushButton#primaryButton:hover {
    background-color: #00f5ff;
}

QPushButton#dangerButton {
    border-color: #ff4757;
    color: #ff4757;
}

QPushButton#dangerButton:hover {
    background-color: #ff4757;
    color: white;
}

QPushButton#successButton {
    border-color: #2ed573;
    color: #2ed573;
}

QPushButton#successButton:hover {
    background-color: #2ed573;
    color: #1a1a2e;
}

QTableWidget {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 8px;
    gridline-color: #0f3460;
    selection-background-color: #00d9ff;
    selection-color: #1a1a2e;
}

QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #0f3460;
}

QTableWidget::item:selected {
    background-color: #00d9ff;
    color: #1a1a2e;
}

QHeaderView::section {
    background-color: #0f3460;
    color: #00d9ff;
    padding: 10px;
    border: none;
    font-weight: bold;
    font-size: 13px;
}

QScrollBar:vertical {
    background-color: #16213e;
    width: 12px;
    border-radius: 6px;
}

QScrollBar::handle:vertical {
    background-color: #0f3460;
    border-radius: 6px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background-color: #00d9ff;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #16213e;
    height: 12px;
    border-radius: 6px;
}

QScrollBar::handle:horizontal {
    background-color: #0f3460;
    border-radius: 6px;
    min-width: 30px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #00d9ff;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

QGroupBox {
    border: 2px solid #0f3460;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: bold;
    color: #00d9ff;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 15px;
    padding: 0 8px;
}

QStatusBar {
    background-color: #0f3460;
    color: #888;
    font-size: 12px;
}

QMessageBox {
    background-color: #1a1a2e;
}

QMessageBox QLabel {
    color: #e0e0e0;
}

QMessageBox QPushButton {
    min-width: 80px;
}

QToolTip {
    background-color: #0f3460;
    color: #e0e0e0;
    border: 1px solid #00d9ff;
    border-radius: 4px;
    padding: 6px;
}

QLineEdit {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 15px;
    font-weight: bold;
    color: #ffffff;
    selection-background-color: #00d9ff;
    selection-color: #1a1a2e;
}

QLineEdit:focus {
    border-color: #00d9ff;
    background-color: #1a2a4e;
}

QLineEdit::placeholder {
    color: #666;
}

QSpinBox {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 8px;
    padding: 8px 12px;
    color: #ffffff;
    font-size: 14px;
}

QSpinBox:focus {
    border-color: #00d9ff;
}

QSpinBox::up-button, QSpinBox::down-button {
    background-color: #0f3460;
    border: none;
    width: 20px;
}

QSpinBox::up-button:hover, QSpinBox::down-button:hover {
    background-color: #00d9ff;
}

QCheckBox {
    color: #e0e0e0;
    font-size: 13px;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 2px solid #0f3460;
    border-radius: 4px;
    background-color: #16213e;
}

QCheckBox::indicator:checked {
    background-color: #00d9ff;
    border-color: #00d9ff;
}

QCheckBox::indicator:hover {
    border-color: #00d9ff;
}

QComboBox {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 8px;
    padding: 8px 12px;
    color: #ffffff;
    min-width: 150px;
    font-size: 14px;
}

QComboBox:hover {
    border-color: #00d9ff;
}

QComboBox::drop-down {
    border: none;
    width: 30px;
}

QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 8px solid #00d9ff;
    margin-right: 10px;
}

QComboBox QAbstractItemView {
    background-color: #16213e;
    border: 2px solid #0f3460;
    selection-background-color: #00d9ff;
    selection-color: #1a1a2e;
}

QProgressBar {
    background-color: #16213e;
    border: 2px solid #0f3460;
    border-radius: 8px;
    text-align: center;
    color: #e0e0e0;
}

QProgressBar::chunk {
    background-color: #00d9ff;
    border-radius: 6px;
}
"""

LIGHT_THEME = """
QMainWindow {
    background-color: #f5f6fa;
}

QWidget {
    font-family: "Microsoft YaHei", "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    color: #2f3640;
}

QLabel {
    color: #2f3640;
}

QLabel#titleLabel {
    font-size: 24px;
    font-weight: bold;
    color: #0984e3;
    padding: 10px;
}

QLabel#subtitleLabel {
    font-size: 14px;
    color: #636e72;
    padding-bottom: 20px;
}

QLabel#sectionLabel {
    font-size: 15px;
    font-weight: bold;
    color: #0984e3;
    padding: 5px 0;
}

QTextEdit {
    background-color: white;
    border: 2px solid #dfe6e9;
    border-radius: 8px;
    padding: 12px;
    font-size: 13px;
    color: #2f3640;
    selection-background-color: #0984e3;
    selection-color: white;
}

QTextEdit:focus {
    border-color: #0984e3;
}

QPushButton {
    background-color: white;
    border: 2px solid #0984e3;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 14px;
    font-weight: bold;
    color: #0984e3;
    min-width: 120px;
}

QPushButton:hover {
    background-color: #0984e3;
    color: white;
}

QPushButton#primaryButton {
    background-color: #0984e3;
    color: white;
}

QPushButton#primaryButton:hover {
    background-color: #0652DD;
}

QTableWidget {
    background-color: white;
    border: 2px solid #dfe6e9;
    border-radius: 8px;
    gridline-color: #dfe6e9;
}

QHeaderView::section {
    background-color: #0984e3;
    color: white;
    padding: 10px;
    border: none;
    font-weight: bold;
}

QStatusBar {
    background-color: #dfe6e9;
    color: #636e72;
}
"""
