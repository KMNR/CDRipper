import random
from random import randint

def good1():    #adjective phrase, then noun phrase
    adjective = ["a timeless", 
                 "what a", 
                 "the gods bow before this"]
    noun = ["classic", 
            "record", 
            "monolith of human accomplishment"]

    phrase = random.choice(adjective) + " " + random.choice(noun) + "!"
    return phrase

def good2():    #compliments of instruments
    adjective = ["awesome", 
                 "incredibly quick", 
                 "funky",
                 "meaningful"]
    instrument = ["guitar", 
                  "bass", 
                  "drum",
                  "piano",
                  "tambourine"]
    noun = ["work", "solos", "riffs", "beats"]

    phrase = random.choice(adjective) + " " + random.choice(instrument) \
        + " " + random.choice(noun) + "!"
    return phrase
    
def good3():    #feelings
    adjective = ["deeply", 
                 "incredibly", 
                 "quietly",
                 "intentionally"]
    feel = ["funky", 
            "introspective", 
            "like eating steak",
            "considerate",
            "like rocking out"]
    emoticon = [":-)",
                ":-D",
                ";-P",
                "<3"]

    phrase = "makes me feel" + " " + random.choice(adjective) + " " + \
        random.choice(feel) + " " + random.choice(emoticon)
    return phrase    

def bad1():    #questions
    opener = ["I want to fire the people who",
              "why would anyone bother to",]
    verb = ["invent", "record", "save", "write"]
    link = ["such", "this"]
    noun = ["contrived shit",
            "hipster garbage", 
            "week-old offal"]
    punctuation = ["...",
                   ".",
                   "!"]
    
    phrase = random.choice(opener) + " " + random.choice(verb) + " " + \
        random.choice(link) + " " + random.choice(noun) + \
        random.choice(punctuation)
    return phrase
    
def bad2():     #instrumental critiques
    adjective = ["out of tune", 
                 "remedial", 
                 "needs more",
                 "rhythmless"]
    instrument = ["cowbell", 
                  "vocals", 
                  "didgeridoo",
                  "violin",
                  "drum machine"]
    emoticon = [":-(",
                "D:",
                "D-:<",
                ":'("]
    
    phrase = random.choice(adjective) + " " + random.choice(instrument) \
        + " " + random.choice(emoticon)
    return phrase
    
def spam():
    verb = ["buy",
            "purchase"]
    noun = ["this album",
            "this deliciousness",
            "this and others like it"]
    store = ["amazon.com",
             "walmart.com",
             "itunes.com",
             "thepiratebay.se"]
     
    phrase = random.choice(verb) + " " + random.choice(noun) + \
        " at " + random.choice(store) + "."
    return phrase

def phrase():
    return random.choice([good1(),good2(),good3()]*5+[bad1(),bad2()]*2+[spam()])
