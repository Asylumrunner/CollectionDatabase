import requests
from secrets import secrets

class SeattlePublicLibrary():
    def __init__(self):
        self.Socrata_API_Key = secrets['Socrata_API_Key']
        self.header = {'X-App-Token': self.Socrata_API_Key}
        self.request_template = "https://data.seattle.gov/resource/6vkj-f5xf.json?$where=ISBN%20like%20'%25{}%25'"
    
    def search_collection_by_isbn(self, isbn):
        response = {'status': 'FAIL'}
        try:
            lib_response = requests.get(self.request_template.format(isbn), headers=self.header)
            response['library_response'] = lib_response.json()
            response['status'] = 'OK'
        except Exception as e:
            print("Exception while querying Seattle library for isbn {}: {}".format(isbn, e))
            response['error_message'] = str(e)
        return response