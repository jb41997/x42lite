# -*- mode: python ; coding: utf-8 -*-

block_cipher = None


a = Analysis(['/Users/gryzzlydev/.virtualenvs/x42lite/src/main/python/main.py'],
             pathex=['/Users/gryzzlydev/.virtualenvs/x42lite/target/PyInstaller'],
             binaries=[],
             datas=[],
             hiddenimports=[],
             hookspath=['/Users/gryzzlydev/.virtualenvs/x42lite/venv/lib/python3.7/site-packages/fbs/freeze/hooks'],
             runtime_hooks=['/var/folders/0f/cds5n35s10n3_p1jndxyffn80000gn/T/tmp8fn6w0vy/fbs_pyinstaller_hook.py'],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='x42lite',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=False,
          console=False , icon='/Users/gryzzlydev/.virtualenvs/x42lite/target/Icon.icns')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=False,
               upx_exclude=[],
               name='x42lite')
app = BUNDLE(coll,
             name='x42lite.app',
             icon='/Users/gryzzlydev/.virtualenvs/x42lite/target/Icon.icns',
             bundle_identifier=None)
