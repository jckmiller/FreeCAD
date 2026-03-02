# SPDX-License-Identifier: LGPL-2.1-or-later

set(AIAssistant_Scripts
    Init.py
    InitGui.py
    AIAssistantCore.py
    AIAssistantGui.py
    TestAIAssistant.py
    README.md
)

set(AIAssistant_Icons
    Resources/icons/AIAssistantWorkbench.svg
)

add_custom_target(AIAssistantScripts ALL
    SOURCES ${AIAssistant_Scripts}
)

fc_target_copy_resource_flat(AIAssistantScripts
    ${CMAKE_CURRENT_SOURCE_DIR}
    ${CMAKE_BINARY_DIR}/Mod/AIAssistant
    ${AIAssistant_Scripts}
)

fc_copy_sources(AIAssistantScripts
    "${CMAKE_BINARY_DIR}/${CMAKE_INSTALL_DATADIR}/Mod/AIAssistant"
    ${AIAssistant_Icons}
)

install(
    FILES
        ${AIAssistant_Scripts}
    DESTINATION
        Mod/AIAssistant
)

install(
    FILES
        ${AIAssistant_Icons}
    DESTINATION
        Mod/AIAssistant/Resources/icons
)
