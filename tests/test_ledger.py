"""Optional source-level check for the empty synthetic ledger starter."""
import json
from pathlib import Path
import shutil, subprocess, unittest

ROOT=Path(__file__).resolve().parents[1]

class LedgerStarterTests(unittest.TestCase):
    def test_date_bounds_integer_money_and_transfer_conservation(self):
        node=shutil.which('node')
        if not node:self.skipTest('Node unavailable; optional React-example state helper check not run')
        source=str(ROOT/'library/examples/local-ledger/data.js')
        code="""
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const m=await import('data:text/javascript;base64,'+readFileSync(SOURCE).toString('base64'));
assert.deepEqual(m.SEED,[]);
assert.equal(m.validDate('2025-01-14'),true);
assert.equal(m.validDate('2024-12-31'),false);
assert.equal(m.validDate('2025-02-01'),false);
assert.equal(m.validDate('2025-02-31'),false);
assert.equal(m.parseAmount('12,34'),1234);
assert.equal(m.parseAmount('12.345'),null);
const income={id:'i',date:'2025-01-14',type:'income',amountKopecks:25000,accountId:'daily',categoryId:null,toAccountId:null,note:'Synthetic income'};
const transfer={id:'t',date:'2025-01-15',type:'transfer',amountKopecks:1000,accountId:'daily',categoryId:null,toAccountId:'reserve',note:'Synthetic transfer'};
assert.equal(m.validateRecord(income),true);assert.equal(m.validateRecord(transfer),true);
assert.equal(m.accountBalance([income,transfer],'daily'),24000);
assert.equal(m.accountBalance([income,transfer],'reserve'),1000);
assert.equal(m.totals([income,transfer],'2025-01').income,25000);
assert.equal(m.totals([income,transfer],'2025-01').expense,0);
""".replace('SOURCE',json.dumps(source))
        r=subprocess.run([node,'--input-type=module','-e',code],capture_output=True,text=True)
        self.assertEqual(r.returncode,0,r.stdout+r.stderr)

if __name__=='__main__':unittest.main(verbosity=2)
