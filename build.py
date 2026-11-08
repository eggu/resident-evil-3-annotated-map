"""Build RE3.AnnotatedMap.asi (x86 Windows, zig cc) and the HD atlas files; never touches the game."""
import importlib, os, shutil, subprocess, sys, zipfile, hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NAME = 'RE3.AnnotatedMap.asi'
# ponytail: Plant header reuses third-party HD glyphs; the native SD header is shown instead.
EXCLUDED_HD = {'4D420B84.webp'}


def main():
    build = ROOT / 'build'
    build.mkdir(exist_ok=True)
    zig_lib = Path(importlib.import_module('ziglang').__file__).parent / 'lib'
    subprocess.run([sys.executable, '-m', 'ziglang', 'cc', '-target', 'x86-windows-gnu', '-shared', '-O2',
                    '-fno-stack-protector', '-DWIN32_LEAN_AND_MEAN', '-nostdlib', '-Wall', '-Wextra',
                    f'-I{zig_lib}/libc/include/any-windows-any', f'-I{ROOT / "src"}', '-Wl,--entry,DllMain@12',
                    str(ROOT / 'src/re3_map.c'), '-lkernel32', '-luser32', '-o', str(build / NAME)], check=True)
    version = (ROOT / 'VERSION').read_text().strip()
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    # RE3_CANDIDATE=<n> writes a numbered test candidate instead of the release ZIP, which is never rebuilt over.
    candidate = os.environ.get('RE3_CANDIDATE')
    package = dist / (f'RE3-Annotated-Map-{version}-candidate-{candidate}.zip' if candidate else f'RE3-Annotated-Map-{version}.zip')
    if package.exists() and not os.environ.get('RE3_REPLACE'):
        sys.exit(f'{package.name} exists; a built ZIP is never overwritten (RE3_REPLACE=1 to replace it on purpose)')
    with zipfile.ZipFile(package, 'w', zipfile.ZIP_DEFLATED) as z:
        z.write(build / NAME, NAME)
        for p in sorted((build / 'hires/misc').glob('*.webp')):
            if p.name not in EXCLUDED_HD:
                z.write(p, f'hires/misc/{p.name}')
        z.write(ROOT / 'packaging/README.txt', 'README-AnnotatedMap.txt')
        z.write(ROOT / 'packaging/RE3.AnnotatedMap.ini', 'RE3.AnnotatedMap.ini')   # defaults; an existing user INI is never replaced (README)
        z.write(ROOT / 'LICENSE', 'LICENSE.txt')
        z.write(ROOT / 'NOTICE.md', 'NOTICE.md')
    report = dict(version=version, asi_sha256=hashlib.sha256((build / NAME).read_bytes()).hexdigest(),
                  package=package.name, files=zipfile.ZipFile(package).namelist())
    (build / 'build-report.json').write_text(json.dumps(report, indent=1) + '\n')
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
