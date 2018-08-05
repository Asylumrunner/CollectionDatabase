import pprint
import json

with open('test.txt', 'r') as file:
    response = json.load(file)
    pp = pprint.PrettyPrinter()
    pp.pprint(response)
