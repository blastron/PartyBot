pronounceableNames = {
    "adamth3walker": "adam the walker",
    "a-zu-ra": "ah-zoo-ra",
    "beetie swelle": "beedee swell",
    "cii": "see",
    "cjthemusicdude": "CJ the music dude",
    "draconiator": "druh cone ee ator",
    "dusthillguy": "dusthill guy",
    "johnfn": "john FN",
    "mcmiagblackmanisgod": "my cutie mark is a gun, black man is god",
    "misael.k": "me-sigh-ale ka",
    "omgitslewis": "oh em gee it's lewis",
    "patashu": "pat-a-shoe",
    "sci": "sigh",
    "seventhelement": "seventh element",
    "shadow psyclone": "shadow cyclone",
    "somasis": "so may sis",
    "somasismakesbadstuff": "so may sis makes bad stuff",
    "supaspeedstrut": "supa speed strut",
    "suzumebachi": "sue-zoo-may-bah-chee",
    "trancient": "tran-see-ent",
    "wolfofsadness": "wolf of sadness"
}

def GetPronounceableName(baseName):
    if baseName.lower() in pronounceableNames.keys():
        return pronounceableNames[baseName.lower()]
    else: return baseName