import os
from googleapiclient.discovery import build  # type: ignore


class GoogleSearch():
    def __init__(self):
        # init google search engine
        self.service = build(
            "customsearch", "v1", developerKey=os.getenv("GOOGLE_API_TOKEN")
        )

    def search(self, query):
        # call google search api
        response = (
            self.service.cse()
            .list(
                q=query,
                cx=os.getenv("GOOGLE_API_ID"),
            )
            .execute()
        )
        return response['items']
