from pprint import pprint

import pyeodh

c = pyeodh.Client(base_url="https://api.stac.ceda.ac.uk")
rc = c.get_resource_catalog()

# for col in rc.get_collections():
#     print(col.description)

print(rc.get_collection("cmip6").description)
