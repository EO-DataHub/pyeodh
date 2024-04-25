from pprint import pprint

import pyeodh

c = pyeodh.Client()
rc = c.get_resource_catalog()
# pprint(rc._raw_data)
# pprint(rc.get_collections())
# for col in rc.get_collections():
#     print(col.description)

# print(rc.get_collection("cmip6").description)
items = rc.get_collection("cmip6").get_items()
for item in items:
    print(item.id)
