pronounceableNames = {
    "adamth3walker": "adam the walker",
    "akogarezephyr": "Ah-Ko-Gah-Ray zephyr",
    "arcana": "arcayna",
    "atmospherium": "atmosphirium",
    "a-zu-ra": "ah-zoo-ra",
    "beetie swelle": "beedee swell",
    "blastron": "blast tron",
    "cii": "see",
    "cjthemusicdude": "CJ the music dude",
    "darthpolly": "darth polly",
    "draconiator": "druh cone ee ator",
    "dusthillguy": "dusthill guy",
    "gercr": "jer",
    "johnfn": "john FN",
    "koekepan": "kookah pawn",
    "mcmiagblackmanisgod": "my cutie mark is a gun, black man is god",
    "mirby": "murby",
    "misael.k": "me-sigh-ale ka",
    "neukatalyst": "new catalyst",
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
