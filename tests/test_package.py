import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
class PackageTests(unittest.TestCase):
    def test_portable_readback_and_extracted_cli(self):
        with tempfile.TemporaryDirectory() as name:
            temp=Path(name).resolve(); archive=temp/'portable.zip'
            result=subprocess.run([sys.executable,str(ROOT/'scripts/package.py'),'--out',str(archive)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            with zipfile.ZipFile(archive) as package:
                names=package.namelist(); self.assertIn('workbench.json',names); self.assertIn('SKILL.md',names); self.assertIn('scripts/install.py',names); self.assertIn('references/implementation.md',names)
                self.assertFalse(any('.git' in Path(n).parts or '.github' in Path(n).parts or 'private' in Path(n).parts or '__pycache__' in Path(n).parts or 'dist' in Path(n).parts or 'node_modules' in Path(n).parts for n in names))
                assets=json.loads(package.read('examples/showcase/assets.json'))['assets']
                approved_pngs={item['path'] for item in assets if item['kind']=='png'}
                self.assertTrue(approved_pngs)
                self.assertEqual({n for n in names if n.endswith('.png')},approved_pngs)
                self.assertEqual({n for n in names if n.endswith('.ttf')},{item['path'] for item in assets if item['kind']=='ttf'})
                package.extractall(temp/'extracted')
            public_check=subprocess.run([sys.executable,str(temp/'extracted/scripts/check_public.py')],capture_output=True,text=True)
            self.assertEqual(public_check.returncode,0,public_check.stdout+public_check.stderr)
            installed=temp/'installed-skill'
            install_result=subprocess.run([sys.executable,str(temp/'extracted/scripts/install.py'),'--host','codex','--destination',str(installed)],capture_output=True,text=True)
            self.assertEqual(install_result.returncode,0,install_result.stdout+install_result.stderr)
            self.assertTrue((installed/'SKILL.md').is_file())
            run=temp/'fresh-workspace'; run.mkdir()
            (run/'task.json').write_text(json.dumps({'job':'portable fixture','scope':'one screen','factual_data':['synthetic'],'interactions':['open'],'constraints':['offline']}))
            result=subprocess.run([sys.executable,str(installed/'scripts/pipeline.py'),'--workspace',str(run),'create','--task','task.json','--campaign','portable'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stdout+result.stderr)
            repeat=subprocess.run([sys.executable,str(ROOT/'scripts/package.py'),'--out',str(archive)],capture_output=True,text=True)
            self.assertEqual(repeat.returncode,2)
if __name__=='__main__': unittest.main(verbosity=2)
