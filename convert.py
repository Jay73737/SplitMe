import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"   # ← force headless mode

import sys
from pathlib import Path

from PyQt6.QtWidgets  import QApplication
from PyQt6.QtCore     import QFile, QFileDevice
from PyQt6.QtDesigner import QFormBuilder


from main import MainGUI

app = QApplication(sys.argv)

widget = MainGUI()

builder = QFormBuilder()
out_path = Path(__file__).with_name("MainGUI.ui")
qfile    = QFile(str(out_path))

if not qfile.open(QFile.OpenModeFlag.WriteOnly | QFile.OpenModeFlag.Text):
    raise RuntimeError(f"Cannot open {out_path} for writing")

if not builder.save(qfile, widget):
    raise RuntimeError("QFormBuilder.save() returned False")

qfile.close()
print(f"✅  Wrote {out_path}")