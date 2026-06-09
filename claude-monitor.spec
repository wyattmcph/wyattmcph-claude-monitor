# PyInstaller spec for claude-monitor
# Builds a single-file console executable for Windows, macOS, and Linux.
# Run:  pyinstaller claude-monitor.spec
#
# The resulting binary is in dist/claude-monitor  (or dist/claude-monitor.exe on Windows)

import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# Pull in pytz and tzdata timezone data files so date/time handling works
# correctly in the bundled executable.
datas = []
for pkg in ('pytz', 'tzdata'):
    try:
        datas += collect_data_files(pkg)
    except Exception:
        pass

# Hidden imports: modules that PyInstaller's static analysis misses because
# they are imported inside functions, inside try/except blocks, or imported
# via lazy patterns used by pydantic/rich.
hiddenimports = [
    # ── Our own modules (many are imported lazily inside functions) ─────────
    'claude_monitor',
    'claude_monitor._version',
    'claude_monitor.error_handling',
    'claude_monitor.cli',
    'claude_monitor.cli.main',
    'claude_monitor.cli.bootstrap',
    'claude_monitor.core',
    'claude_monitor.core.calculations',
    'claude_monitor.core.data_processors',
    'claude_monitor.core.models',
    'claude_monitor.core.p90_calculator',
    'claude_monitor.core.plans',
    'claude_monitor.core.pricing',
    'claude_monitor.core.settings',
    'claude_monitor.data',
    'claude_monitor.data.aggregator',
    'claude_monitor.data.analysis',
    'claude_monitor.data.analyzer',
    'claude_monitor.data.keyword_analyzer',
    'claude_monitor.data.reader',
    'claude_monitor.monitoring',
    'claude_monitor.monitoring.data_manager',
    'claude_monitor.monitoring.orchestrator',
    'claude_monitor.monitoring.session_monitor',
    'claude_monitor.terminal',
    'claude_monitor.terminal.console_setup',
    'claude_monitor.terminal.icons',
    'claude_monitor.terminal.manager',
    'claude_monitor.terminal.themes',
    'claude_monitor.ui',
    'claude_monitor.ui.adaptive_layout',
    'claude_monitor.ui.components',
    'claude_monitor.ui.config_menu',
    'claude_monitor.ui.dashboard',
    'claude_monitor.ui.display_controller',
    'claude_monitor.ui.key_handler',
    'claude_monitor.ui.keyword_panel',
    'claude_monitor.ui.layouts',
    'claude_monitor.ui.popup_window',
    'claude_monitor.ui.progress_bars',
    'claude_monitor.ui.session_display',
    'claude_monitor.ui.table_views',
    'claude_monitor.utils',
    'claude_monitor.utils.formatting',
    'claude_monitor.utils.model_utils',
    'claude_monitor.utils.notifications',
    'claude_monitor.utils.time_utils',
    'claude_monitor.utils.timezone',
    'claude_monitor.utils.update_check',
    # ── Third-party ─────────────────────────────────────────────────────────
    'watchdog.observers.polling',   # fallback observer, may not be auto-detected
    'tkinter',                      # popup window
    'tkinter.font',
    'importlib.metadata',
    'pkg_resources',
    'pydantic',
    'pydantic.v1',                  # pydantic v2 compatibility shim
    'pydantic_settings',
    'pydantic_settings.main',
    'rich',
    'rich.console',
    'rich.live',
    'rich.text',
    'rich.rule',
    'rich.table',
    'rich.panel',
    'rich.theme',
    'rich.prompt',
    'rich.progress',
    'pytz',
    'numpy',
]

a = Analysis(
    ['_pyinstaller_entry.py'],
    pathex=['src'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'test',
        'tests',
        'pytest',
        'matplotlib',
        'PIL',
        'scipy',
        'pandas',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='claude-monitor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # disabled — UPX not always available on CI runners
    console=True,       # terminal application, must stay console mode
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
