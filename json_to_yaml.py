import json
import yaml

with open('db.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('data.yaml', 'w', encoding='utf-8') as f:
    yaml.dump(data, f, allow_unicode=True, sort_keys=False)

print("แปลง db.json → data.yaml สำเร็จ!")
