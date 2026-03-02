# SPDX-License-Identifier: LGPL-2.1-or-later

import os

import FreeCAD as App
import FreeCADGui as Gui


class AIAssistantWorkbench(Gui.Workbench):
    """AI Assistant workbench object."""

    def __init__(self):
        self.__class__.Icon = os.path.join(
            App.getResourceDir(),
            "Mod",
            "AIAssistant",
            "Resources",
            "icons",
            "AIAssistantWorkbench.svg",
        )
        self.__class__.MenuText = "AI Assistant"
        self.__class__.ToolTip = "AI-assisted FreeCAD Python generation"

    def Initialize(self):
        import AIAssistantGui

        AIAssistantGui.register_commands()
        commands = ["AIAssistant_ToggleDock"]
        self.appendToolbar("AI Assistant", commands)
        self.appendMenu("AI Assistant", commands)

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(AIAssistantWorkbench())

