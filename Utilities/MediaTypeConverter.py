class MediaTypeConverter():
    def __init__(self):
        self.lookupDict = {
            "book": 99,
            "movie": 100,
            "video_game": 101,
            "board_game": 102,
            "rpg": 103,
            "anime": 104,
            "album": 105
        }
    
    def mediaTypeToKey(self, typeName):
        if typeName not in self.lookupDict:
            raise KeyError(f'{typeName} is not a valid media type')
        return self.lookupDict[typeName]
    
    def keyToMediaType(self, key):
        typeNames = [key for key, val in self.lookupDict.items() if val == key]
        if not key:
            raise KeyError(f'{key} is not a valid media type key')
        elif len(typeNames) > 1:
            raise RuntimeError(f'{key} is not unique in media type key lookup dict. Something is disastrously wrong')
        return typeNames[0]