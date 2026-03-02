# SPDX-License-Identifier: LGPL-2.1-or-later

import datetime
import json
import traceback
import urllib.error
import urllib.request

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

from AIAssistantCore import build_messages, extract_code_block, parse_sse_data_line


PARAM_PATH = "User parameter:BaseApp/Preferences/Mod/AIAssistant"
DOCK_OBJECT_NAME = "AIAssistantDock"


def _params():
    return App.ParamGet(PARAM_PATH)


class OpenRouterStreamWorker(QtCore.QObject):
    token = QtCore.Signal(str)
    status = QtCore.Signal(str)
    error = QtCore.Signal(str)
    finished = QtCore.Signal(str, bool)

    def __init__(self, endpoint, api_key, payload):
        super(OpenRouterStreamWorker, self).__init__()
        self.endpoint = endpoint
        self.api_key = api_key
        self.payload = payload
        self._cancelled = False

    @QtCore.Slot()
    def cancel(self):
        self._cancelled = True

    @QtCore.Slot()
    def run(self):
        collected = []
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(self.payload).encode("utf-8"),
            headers={
                "Authorization": "Bearer {0}".format(self.api_key),
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            method="POST",
        )

        try:
            self.status.emit("Connecting to OpenRouter...")
            with urllib.request.urlopen(req, timeout=180) as response:
                self.status.emit("Streaming response...")
                for raw_line in response:
                    if self._cancelled:
                        self.status.emit("Generation cancelled")
                        self.finished.emit("".join(collected), True)
                        return

                    line = raw_line.decode("utf-8", errors="ignore")
                    kind, value = parse_sse_data_line(line)
                    if kind == "done":
                        break
                    if kind == "error":
                        message = value or "Unknown API error"
                        self.error.emit(message)
                        self.finished.emit("".join(collected), False)
                        return

                    piece = value if kind == "token" else ""
                    if piece:
                        collected.append(piece)
                        self.token.emit(piece)

            self.status.emit("Generation completed")
            self.finished.emit("".join(collected), False)
        except urllib.error.HTTPError as err:
            details = err.read().decode("utf-8", errors="ignore")
            self.error.emit("HTTP {0}: {1}".format(err.code, details or err.reason))
            self.finished.emit("".join(collected), False)
        except Exception as err:
            self.error.emit(str(err))
            self.finished.emit("".join(collected), False)


class AIAssistantDock(QtWidgets.QDockWidget):
    def __init__(self, parent=None):
        super(AIAssistantDock, self).__init__(parent)
        self.setObjectName(DOCK_OBJECT_NAME)
        self.setWindowTitle("AI Assistant")
        self.setWindowIcon(
            QtGui.QIcon(
                App.getResourceDir()
                + "Mod/AIAssistant/Resources/icons/AIAssistantWorkbench.svg"
            )
        )

        self._thread = None
        self._worker = None
        self._raw_response = ""
        self._current_code = ""
        self._run_history = []

        self._build_ui()
        self._load_settings()

    def _build_ui(self):
        container = QtWidgets.QWidget(self)
        layout = QtWidgets.QVBoxLayout(container)

        settings_group = QtWidgets.QGroupBox("OpenRouter")
        settings_form = QtWidgets.QFormLayout(settings_group)

        self.api_key_edit = QtWidgets.QLineEdit()
        self.api_key_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("sk-or-v1-...")

        self.model_edit = QtWidgets.QLineEdit()
        self.model_edit.setPlaceholderText("openai/gpt-4o-mini")

        self.temperature_spin = QtWidgets.QDoubleSpinBox()
        self.temperature_spin.setDecimals(2)
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.05)

        self.max_tokens_spin = QtWidgets.QSpinBox()
        self.max_tokens_spin.setRange(64, 8192)

        settings_form.addRow("API Key", self.api_key_edit)
        settings_form.addRow("Model", self.model_edit)
        settings_form.addRow("Temperature", self.temperature_spin)
        settings_form.addRow("Max tokens", self.max_tokens_spin)

        self.prompt_edit = QtWidgets.QPlainTextEdit()
        self.prompt_edit.setPlaceholderText(
            "Describe the FreeCAD model/script you want to generate..."
        )

        self.preview_edit = QtWidgets.QPlainTextEdit()
        self.preview_edit.setPlaceholderText("Generated Python code appears here")

        button_row = QtWidgets.QHBoxLayout()
        self.generate_button = QtWidgets.QPushButton("Generate")
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.run_button = QtWidgets.QPushButton("Run in Python")
        self.clear_button = QtWidgets.QPushButton("Clear")

        self.cancel_button.setEnabled(False)
        self.run_button.setEnabled(False)

        button_row.addWidget(self.generate_button)
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.run_button)
        button_row.addWidget(self.clear_button)

        self.status_label = QtWidgets.QLabel("Idle")
        self.status_label.setWordWrap(True)

        layout.addWidget(settings_group)
        layout.addWidget(QtWidgets.QLabel("Prompt"))
        layout.addWidget(self.prompt_edit, 1)
        layout.addLayout(button_row)
        layout.addWidget(QtWidgets.QLabel("Generated Python"))
        layout.addWidget(self.preview_edit, 2)
        layout.addWidget(self.status_label)

        self.setWidget(container)

        self.generate_button.clicked.connect(self.on_generate)
        self.cancel_button.clicked.connect(self.on_cancel)
        self.run_button.clicked.connect(self.on_run)
        self.clear_button.clicked.connect(self.on_clear)

    def _load_settings(self):
        p = _params()
        # Do not persist API keys; require per-session entry.
        self.api_key_edit.clear()
        self.model_edit.setText(p.GetString("OpenRouterModel", "openai/gpt-4o-mini"))
        self.temperature_spin.setValue(p.GetFloat("Temperature", 0.2))
        self.max_tokens_spin.setValue(p.GetInt("MaxTokens", 1200))

    def _save_settings(self):
        p = _params()
        # Remove any previously persisted key from older versions.
        p.RemString("OpenRouterApiKey")
        p.SetString("OpenRouterModel", self.model_edit.text().strip())
        p.SetFloat("Temperature", self.temperature_spin.value())
        p.SetInt("MaxTokens", int(self.max_tokens_spin.value()))
        p.SetString("Endpoint", "https://openrouter.ai/api/v1/chat/completions")

    def _set_generating(self, generating):
        self.generate_button.setEnabled(not generating)
        self.cancel_button.setEnabled(generating)
        self.run_button.setEnabled((not generating) and bool(self._current_code.strip()))

    def _build_messages(self):
        doc_name = App.ActiveDocument.Name if App.ActiveDocument else "NoActiveDocument"
        user_prompt = self.prompt_edit.toPlainText().strip()
        return build_messages(user_prompt, doc_name)

    def _set_status(self, text):
        self.status_label.setText(text)

    @QtCore.Slot()
    def on_generate(self):
        prompt = self.prompt_edit.toPlainText().strip()
        api_key = self.api_key_edit.text().strip()
        model = self.model_edit.text().strip()

        if not prompt:
            QtWidgets.QMessageBox.warning(self, "AI Assistant", "Prompt is empty.")
            return
        if not api_key:
            QtWidgets.QMessageBox.warning(self, "AI Assistant", "OpenRouter API key is required.")
            return
        if not model:
            QtWidgets.QMessageBox.warning(self, "AI Assistant", "Model is required.")
            return

        self._save_settings()
        self._raw_response = ""
        self._current_code = ""
        self.preview_edit.clear()
        self._set_generating(True)

        payload = {
            "model": model,
            "messages": self._build_messages(),
            "temperature": float(self.temperature_spin.value()),
            "max_tokens": int(self.max_tokens_spin.value()),
            "stream": True,
        }
        endpoint = _params().GetString(
            "Endpoint", "https://openrouter.ai/api/v1/chat/completions"
        )

        self._thread = QtCore.QThread(self)
        self._worker = OpenRouterStreamWorker(endpoint, api_key, payload)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.token.connect(self._on_stream_token)
        self._worker.status.connect(self._set_status)
        self._worker.error.connect(self._on_stream_error)
        self._worker.finished.connect(self._on_stream_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    @QtCore.Slot(str)
    def _on_stream_token(self, token):
        self._raw_response += token
        cursor = self.preview_edit.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(token)
        self.preview_edit.setTextCursor(cursor)

    @QtCore.Slot(str)
    def _on_stream_error(self, message):
        self._set_status("Error: {0}".format(message))
        App.Console.PrintError("AIAssistant: {0}\n".format(message))

    @QtCore.Slot(str, bool)
    def _on_stream_finished(self, _full_text, cancelled):
        cleaned = extract_code_block(self._raw_response)
        self._current_code = cleaned
        if cleaned:
            self.preview_edit.setPlainText(cleaned)
        if cancelled:
            self._set_status("Cancelled")
        elif cleaned:
            self._set_status("Ready to run")
        else:
            self._set_status("No code returned")
        self._set_generating(False)

    @QtCore.Slot()
    def on_cancel(self):
        if self._worker is not None:
            self._worker.cancel()

    @QtCore.Slot()
    def on_clear(self):
        self.prompt_edit.clear()
        self.preview_edit.clear()
        self._raw_response = ""
        self._current_code = ""
        self._set_status("Cleared")
        self._set_generating(False)

    @QtCore.Slot()
    def on_run(self):
        code = self.preview_edit.toPlainText().strip()
        if not code:
            QtWidgets.QMessageBox.warning(self, "AI Assistant", "No code to run.")
            return

        try:
            namespace = {
                "App": App,
                "Gui": Gui,
                "FreeCAD": App,
                "FreeCADGui": Gui,
            }
            compiled = compile(code, "<AIAssistantGenerated>", "exec")
            exec(compiled, namespace, namespace)
            self._run_history.append(
                {
                    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
                    "code": code,
                }
            )
            _params().SetString("LastRunCode", code)
            _params().SetInt("RunCount", len(self._run_history))
            App.Console.PrintMessage("AIAssistant: generated code executed\n")
            self._set_status("Code executed")
        except Exception as err:
            tb = traceback.format_exc()
            App.Console.PrintError(tb + "\n")
            QtWidgets.QMessageBox.critical(
                self,
                "AI Assistant",
                "Execution failed:\n{0}".format(err),
            )
            self._set_status("Execution failed")


class CommandToggleAIAssistantDock:
    def GetResources(self):
        return {
            "Pixmap": "AIAssistantWorkbench",
            "MenuText": "AI Assistant",
            "ToolTip": "Show/hide AI Assistant dock",
        }

    def IsActive(self):
        return Gui.Up

    def Activated(self):
        dock = get_or_create_dock()
        if dock.isVisible():
            dock.hide()
        else:
            dock.show()
            dock.raise_()


def get_or_create_dock():
    mw = Gui.getMainWindow()
    dock = mw.findChild(QtWidgets.QDockWidget, DOCK_OBJECT_NAME)
    if dock is None:
        dock = AIAssistantDock(mw)
        mw.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
    return dock


def register_commands():
    Gui.addCommand("AIAssistant_ToggleDock", CommandToggleAIAssistantDock())
