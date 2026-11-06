import collections
import json

with open("wiki.json", encoding="utf-16") as handle:
    data = json.load(handle)

counts = collections.Counter(
    (item["severity"], item["messages"][0][:70]) for item in data["findings"]
)
for (severity, message), number in counts.most_common(15):
    print(number, severity, message)