# AI Assistant Workbench

This module adds a dedicated FreeCAD workbench for AI-assisted Python generation using OpenRouter.

## Features

- Dockable panel with prompt input, Generate, Cancel, Run, and Clear actions.
- Streaming token updates into a code preview editor.
- Explicit run-only behavior: generated code is never executed automatically.
- API key and model settings stored in FreeCAD user parameters.

## Parameter storage

Settings are stored at:

`User parameter:BaseApp/Preferences/Mod/AIAssistant`

Key fields:

- `OpenRouterApiKey`
- `OpenRouterModel`
- `Temperature`
- `MaxTokens`
- `Endpoint`

## Security model

- No automatic execution path exists.
- User must click **Run in Python** to execute preview content.
- Run is disabled while generation is in progress.

## Manual smoke test

1. Start FreeCAD and activate **AI Assistant** workbench.
2. Open the dock using the **AI Assistant** command.
3. Enter OpenRouter API key and model.
4. Prompt for a simple script, e.g. create a Part cube.
5. Click **Generate** and verify streaming output.
6. Click **Run in Python** and verify object creation in the active document.

