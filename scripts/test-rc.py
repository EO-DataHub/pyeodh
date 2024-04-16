import pyeodh
from pprint import pprint

c = pyeodh.Client(base_url="https://api.stac.ceda.ac.uk")
rc = c.get_resource_catalog()

# pprint(rc._data)
# pprint(rc.collections)
# print(rc.collections[0].get("href"))
pprint(rc.get_collection(rc.collections[0]))
