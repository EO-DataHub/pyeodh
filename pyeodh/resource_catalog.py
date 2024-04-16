import posixpath

from pyeodh.base_object import BaseObject


class Collection(BaseObject):

    @property
    def description(self) -> str:
        return self._description

    def _set_properties(self) -> None:
        self._description = self._raw_data.get("description", None)


class ResourceCatalog(BaseObject):

    @property
    def links(self) -> list[dict]:
        return self._links

    @property
    def collections_url(self) -> str:
        if hasattr(self, "_collections_url"):
            return self._collections_url

        link = next(filter(lambda ln: ln["rel"] == "data", self.links), None)
        self._collections_url = link.get("href")
        return self._collections_url

    def _set_properties(self) -> None:
        self._links = self._raw_data.get("links", None)

    def get_collections(self) -> list[Collection]:
        """Fetches all resource catalog collections.

        Returns:
            list[Collection]: List of available collections
        """

        headers, response = self._client._request_json("GET", self.collections_url)
        collections = []

        for item in response.get("collections"):
            collections.append(Collection(self._client, headers, item))

        return collections

    def get_collection(self, name: str) -> Collection:
        """Fetches a resource catalog collection.

        Args:
            name (str): ID of a collection

        Returns:
            Collection: Collection for given ID
        """
        url = posixpath.join(self.collections_url, name)
        headers, response = self._client._request_json("GET", url)

        return Collection(self._client, headers, response)
