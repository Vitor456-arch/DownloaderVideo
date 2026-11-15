STYLE = """
QWidget { background: #111827; color: #e5eaf3; font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 13px; }
QMainWindow { background: #111827; }
QLabel#brand { color: #ffffff; font-size: 23px; font-weight: 700; }
QLabel#heading { font-size: 26px; font-weight: 700; color: #ffffff; }
QLabel#muted { color: #9aaac2; }
QFrame#sidebar { background: #0b1220; border-right: 1px solid #243047; }
QFrame#sidebar QLabel, QFrame#sidebar QPushButton { background: transparent; }
QPushButton { background: #233149; border: 1px solid #35445f; border-radius: 7px; padding: 9px 15px; }
QPushButton:hover { background: #314461; border-color: #7199cd; }
QPushButton:disabled { color: #68768c; background: #1a2537; }
QPushButton#primary { background: #276ae5; border-color: #4988fa; color: white; font-weight: 600; }
QPushButton#primary:hover { background: #387cf4; }
QPushButton#nav { text-align: left; padding: 13px; border: none; }
QPushButton#nav:checked { background: #1d3356; color: #80b1ff; }
QLineEdit, QPlainTextEdit, QSpinBox, QComboBox { background: #0e1726; border: 1px solid #34435b; border-radius: 5px; padding: 7px; selection-background-color: #2866ca; }
QLineEdit:focus, QPlainTextEdit:focus { border-color: #5796ff; }
QTabWidget::pane { border: 1px solid #2b3b52; border-radius: 5px; }
QTabBar::tab { background: #1b283c; padding: 10px 17px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #8fbcff; border-bottom: 2px solid #4c8ef7; }
QTableWidget, QListWidget { background: #101b2c; alternate-background-color: #162236; border: 1px solid #2b3b52; gridline-color: #26354b; selection-background-color: #234473; }
QHeaderView::section { background: #1b283c; color: #aebed5; padding: 10px; border: none; border-right: 1px solid #2b3b52; }
QProgressBar { border: none; border-radius: 4px; background: #25344c; text-align: center; }
QProgressBar::chunk { background: #3882ed; border-radius: 4px; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QScrollBar:vertical { background: #111827; width: 11px; }
QScrollBar::handle:vertical { background: #35445f; border-radius: 5px; min-height: 25px; }
QToolTip { background: #263850; color: white; border: 1px solid #6082b0; }
"""
