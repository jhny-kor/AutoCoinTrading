# build.spec
from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ['bot_manager.py'],
    pathex=['.'],
    binaries=[],
    datas=[('.env.example', '.')],
    hiddenimports=collect_submodules('ccxt') + ['dotenv'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas,
          name='AutoCoinTrading',
          console=True,  # 콘솔 창 띄움
          onefile=False, # ← onedir 모드 (중요!)
          )
