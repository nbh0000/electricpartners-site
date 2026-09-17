"""Exercise the supplied migrations and worker INSERT on a disposable local SQLite DB."""
from pathlib import Path
import sqlite3, re, json
root=Path(__file__).resolve().parents[1]
db=sqlite3.connect(':memory:')
db.executescript((root/'migrations/0001_inquiries.sql').read_text())
# Simulate one existing, pre-migration inquiry; all values below are dummy data.
db.execute('INSERT INTO inquiries (id,created_at,expires_at,province,city,facility,request_type,start_preference,work_type,phone,privacy_version,privacy_consent,transfer_consent) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)',('EP-LEGACY','2026-09-17','2026-10-17','gyeonggi','siheung','factory','consult','discuss','discuss','010-0000-0000','test',1,0))
db.executescript((root/'migrations/0002_services.sql').read_text())
assert db.execute('SELECT service,inspection_type,shutdown_possible FROM inquiries WHERE id=?',('EP-LEGACY',)).fetchone()==('onsite','discuss','unknown')
worker=(root/'worker/index.js').read_text()
sql=re.search(r'prepare\(`(INSERT INTO inquiries.*?)`\)',worker,re.S).group(1)
for service in ['onsite','duty','both']:
    values=('EP-TEST-'+service,'2026-09-17','2026-10-17','seoul','gangnam','building','consult','discuss','discuss','','','010-0000-0000','','','/','{}','test',1,0,'new',service,'annual' if service!='onsite' else 'discuss','limited' if service!='onsite' else 'unknown')
    assert sql.count('?')==len(values)==23
    db.execute(sql,values)
    assert db.execute('SELECT service FROM inquiries WHERE id=?',(values[0],)).fetchone()[0]==service
result={'localSQLite':True,'liveD1':False,'migrationsApplied':['0001_inquiries.sql','0002_services.sql'],'legacyRecordPreserved':True,'serviceInserts':['onsite','duty','both'],'insertBindings':23,'allPassed':True}
(root/'docs/sqlite-qa.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))
db.close()
