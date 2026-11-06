# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files

datas = [('assets', 'assets'), ('AVISO_USO.txt', '.'), ('LICENSE.txt', '.'), ('LICENCIAS.txt', '.'), ('LICENCIAS_TERCEROS.txt', '.'), ('compilacion.txt', '.')]
datas += collect_data_files('tkinterdnd2')


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=['PIL._tkinter_finder'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['onnxruntime', 'ssl', '_ssl', 'http', 'urllib.request', 'ftplib', 'smtplib', 'poplib', 'imaplib', 'xmlrpc', 'webbrowser', 'socket', '_socket', 'asyncio', '_asyncio', '_overlapped', 'multiprocessing', '_multiprocessing'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Ozone PDF',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon=['assets/icono.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Ozone PDF',
)
