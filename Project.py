import sys
import requests
import re
import spacy
import collections
import csv
import time

def main(argv):
    nlp = spacy.load('en_default') #put this first so we don't load it for every question
    questionCount = 0
    for line in sys.stdin:
        line = line.rstrip() # removes newline

        splitLine = line.split("\t")
        if len(splitLine)>=2:
            line = splitLine[1]
            print(splitLine[0] + "\t", end="")
        else:
            #question withoutnumber
            line = splitLine[0]
            questionCount += 1
            print(str(questionCount) + "\t", end="")

        answer = create_and_fire_query(line, nlp) #returns 1 and prints answer if one was found
        if answer == 0:
            print("No answer found")
        else:
            print("\n", end="")
        #end of file ends program because stdin is used

# def print_example_queries():
#     # don't think we need this ?
#     #print("enter question:")
#     print("\n")
#     return

def read_csv():
    wordfreqs = {}
    with open('WordFreq.csv', 'rt') as csvfile:
        csvreader = csv.reader(csvfile, delimiter=',', quotechar='|')
        for csvline in csvreader:
            wordfreqs[(csvline[1],csvline[2])] = csvline[0]
    return wordfreqs




def test_for_yes_no(line) :
    # TODO: write this function
    # returns 1 if it's a yes/no question, or 0 otherwise
    # I think this is easy, test whether the lemma of the first word is "be" or "do"
    if line[0].lemma_ == 'do' or line[0].lemma_ == 'be':
        return 1
    return 0

try:
    from dateutil.parser import parse
except:
    print("Dateutil not installed")

def is_date(e):
    try:
        parse(e)
        return True
    except:
        return False

def simple_yes_no(line) :
    
    # extract words from the line in order of how likely they are to be important
    entList = []
    entList.extend(extract_named_entities(line))
    entList.extend(extract_adjectives(line))
    entList.extend(free_nouns(line))
    entList.extend(free_verbs(line))
    
    # make pairs
    pairs = []
    Pair =collections.namedtuple('Pair',['ent1','ent2'])
    for ent1 in entList:
        for ent2 in entList:
            
            if ent1 != ent2 and (Pair(str(ent1[0]),str(ent2[0])) not in pairs):
                pairs.append(Pair(str(ent1[0]),str(ent2[0])))
    print(pairs)
    # construct and fire queries
    wdapi = 'https://wikidata.org/w/api.php';
    wdparams = {'action':'wbsearchentities','language':'en', 'format':'json'}
    sparqlurl = 'https://query.wikidata.org/sparql'
    for pair in pairs:
            wdparams['search'] = pair.ent1
            wdparams['type'] = 'item'
            json = requests.get(wdapi,wdparams).json()
            for result in json['search']:
                ent1_id = result['id']
                wdparams['search'] = pair.ent2
                wdparams['type'] = 'item'
                json = requests.get(wdapi,wdparams).json()                
                for result in json['search']:
                    ent2_id = result['id']
                    # queries whether the two objects are related to eachother in any way
                    query = ('SELECT ?answer WHERE {'
                              'OPTIONAL { wd:'+ent1_id+' ?answer wd:'+ent2_id+' . }'
                              'OPTIONAL { wd:'+ent2_id+' ?answer wd:'+ent1_id+'.}}')

                    # this code is changed so that if our connection is refused for too many requests we try again after a shord wait
                    data = ''
                    while data == '':
                        try:
                            data = requests.get(sparqlurl, params = {'query':query, 'format':'json'}).json()
                        except:
                            #print("Connection refused by the server..")
                            time.sleep(5)
                            #print("Was a nice sleep, now let me continue...")
                            continue
                    # if query returned a relation between entities, answer yes
                    if data['results']['bindings'] != [{}]:
                        print("Yes", end='')
                        return
                else: #entity2 did not give results, check if it was a year
                    print("check for year")
                    try: #huge try catch for when dateutil is not installed
                        if pair.ent2.isdigit() or is_date(pair.ent2):
                            print("isdigit")
                            time_properties = ["P569", "P570", "P571", "P580", "P582"] #most common date types
                            for prop in time_properties:
                                answer = ''
                                query = 'SELECT ?answerLabel WHERE { wd:'+ent1_id+' wdt:'+prop+' ?answer. SERVICE wikibase:label {bd:serviceParam wikibase:language "en" .}}'
                                # this code is changed so that if our connection is refused for too many requests we try again after a short wait
                                data = ''
                                while data == '':
                                    try:
                                        data = requests.get(sparqlurl, params = {'query':query, 'format':'json'}).json()
                                    except:
                                        time.sleep(5)
                                        continue
                                
                                for item in data['results']['bindings']:
                                    for key in item:
                                        if item[key]['type'] == 'literal':
                                            print(pair.ent2)
                                            print(item[key]['value'])
                                            if is_date(item[key]['value']):
                                                date = parse(item[key]['value'])
                                                if is_date(pair.ent2): #assumes the question is a year and checks if they are the same
                                                    if str(parse(pair.ent2)) == str(date):
                                                        print("Yes", end='')
                                                        return
                                                else: #its a year
                                                    if pair.ent2 == str(date.year):
                                                        print("Yes", end='')
                                                        return
                    except:
                        #not a date
                        continue


    # if every query failed, answer no
    print("No", end='')


# # no longer used
# def analysis_yes_no(line) :
#     # TODO: write this function
#     # not sure the best way to do this, but can probably use some of the
#     # helper functions for the normal analysis
#     wdapi = 'https://wikidata.org/w/api.php';
#     wdparams = {'action':'wbsearchentities','language':'en', 'format':'json'}
#     phrase = ""
#     entity1 = ""
#     entity2 = ""
#     rel = ""
#     i = 0
#     while i < len(line):
#         # print(str(line[i]))
#         # print(line[i].tag_)
#         if line[i].tag_ == "NN" or line[i].tag_ == "NNS" or line[i].tag_ == "NNP":
#             while line[i].dep_ == "compound":
#                 phrase += str(line[i]) + " "
#                 i+=1 #fill in the first noun phrase
#             if line[i].tag_ == "NNS":
#                 phrase += str(line[i].lemma_)
#             else:
#                 phrase += str(line[i])
#             if entity1 == "":
#                 entity1 += phrase
#                 phrase = ""
#             elif entity2 == "":
#                 entity2 += phrase
#                 phrase = ""
#             elif entity2 != "":
#                 entity2 += " " + phrase
#                 phrase = ""
#         elif (line[i].tag_ == "JJ" or line[i].tag_ == "CD") and entity2 == "": #adds numbers as entity2 if all else fails
#             entity2 += str(line[i])
#         elif line[i].tag_ == "VB":
#             rel += str(line[i].lemma_)
#         i += 1
#     return fire_sparql_yes_no(entity1, rel, entity2)

# #return fire_sparql_yes_no(ob1, rel, ob2)

# #no longer used
# def answer_yes_no(ob1, rel, ob2):
#     print(ob2)
#     url = 'https://query.wikidata.org/sparql'
#     query = 'ASK {wd:'+ob1+' wdt:'+rel+' wd:'+ob2+'.}'
#     result = requests.get(url, params={'query': query, 'format': 'json'}).json()
#     if result['boolean'] == True:
#         answer = 'Yes'
#     elif result['boolean'] == False:
#         answer = 'No'
#     print(answer, end="")

# #no longer used
# def fire_sparql_yes_no(ob1, rel, ob2) :
#     # Searches for the relationship between two objects
#     # Returns booleans
#     entity1_id = ""
#     entity2_id = ""
#     url = 'https://query.wikidata.org/sparql'
#     wdapi = 'https://wikidata.org/w/api.php';
#     wdparams = {'action':'wbsearchentities','language':'en', 'format':'json'}
    
#     wdparams['search'] = ob1
#     wdparams['type'] = 'item'
#     json = requests.get(wdapi, wdparams).json()
#     for result in json['search']:
#         entity1_id = result['id']
#         wdparams['search'] = ob2
#         wdparams['type'] = 'item'
#         json = requests.get(wdapi, wdparams).json()
#         for result in json['search']:
#             entity2_id = result['id']
#             if rel == "":
#                 print("rel empty")
#                 query = 'SELECT ?relation ?relationLabel WHERE {wd:'+entity1_id+' ?relation wd:'+entity2_id+' . SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }}'
#                 data = requests.get(url, params={'query': query, 'format': 'json'}).json()
#                 #for dates/numbers: fails here, no items found
#                 for item in data['results']['bindings']:
#                     for key in item:
#                         if item[key]['type'] == 'literal':
#                             wdparams['search'] = ('{}'.format(item[key]['value']))
#                             wdparams['type'] = 'property'
#                             json = requests.get(wdapi,wdparams).json()
#                             for searchResult in json['search']:
#                                 rel = searchResult['id']
#                                 print(entity1_id, rel, entity2_id)
#                                 return answer_yes_no(entity1_id, rel, entity2_id)
#             else:
#                 wdparams['search'] = rel
#                 wdparams['type'] = 'property'
#                 json = requests.get(wdapi,wdparams).json()
#                 for result in json['search']:
#                     rel = result['id']
#                     return answer_yes_no(entity1_id, rel, entity2_id)
#     print("No", end="")


def test_for_count(line) :
    # TODO: write this function
    # returns 1 if it is a counting question, or 0 if it isnt
    # maybe just check for keywords, like "count" or "how many"?
    #print(line[0].lemma_ + " " + line[1].lemma_)
    if (line[0].lemma_ == 'how' and line[1].lemma_ == 'many') or line[0].lemma_== 'count':
        return 1
    return 0

    
def analysis(line):
    # takes the tokenised line, returns list of variables to query
    WordFreq = read_csv()
    entList = []
    relList = []
    pairs = []
    # Strategy is to have two lists, one of entities and
    # one of relations, compiled so that most reliable options are
    # earlier in the list. Then cycle through the
    # combinations until there is an answer.
    entList.extend(extract_named_entities(line))

    relList.extend(extract_subj(line))
    entList.extend(free_nouns(line))
    relList.extend(free_verbs(line))
    relList.extend(free_nouns(line))
    
    # sorting some of the words by frequency to try the rarest ones first
    entDict = {}
    for item in entList:
        if item not in WordFreq:
            entDict[item] = len(WordFreq)+1
        else:
            entDict[item] = int(WordFreq[item])
    ent_sorted = sorted(entList, key=entDict.get, reverse=True)

    relDict = {}
    for item in relList:
        if item not in WordFreq:
            relDict[item] = len(WordFreq)+1
        else:
            relDict[item] = int(WordFreq[item])
    rel_sorted = sorted(relList, key=relDict.get, reverse=True)

    #this is such a last resort that we add it after sorting, because "List the x of y" gives the wrong answer
    ent_sorted.extend(free_verbs(line))
    
    Pair =collections.namedtuple('Pair',['entity','relation'])
    for ent in ent_sorted:
        for rel in rel_sorted:
            if ent != rel and (Pair(str(ent[0]),str(rel[0])) not in pairs):
                pairs.append(Pair(str(ent[0]),str(rel[0])))
    return pairs


def extract_named_entities(result):
    # Returns a list of all named entities in the input
    out = []
    ent = ""
    started = 0
    for w in result:
        if w.ent_iob != 2 and w.tag_ != "POS":
            # exclude possessive endings
            if w.ent_iob == 1:
                ent+= " "
            else:
                if started == 1:
                    out.append((ent,'n'))
                    ent = ""
                started = 1
            ent += str(w) #w.lemma_ also a poss
        elif started == 1:
            started = 0
            out.append((ent,'n'))
            ent = ""
    if started ==1:
        out.append((ent,'n'))        
    return out


def extract_subj(result):
    # returns every nsubj or dobj of every verb
    out =[]
    for w in result:
        if w.pos == 98:
            # 98 is VERB
            for child in w.children:
                if child.dep_ == "auxpass":
                    for achild in child.children:
                        if achild.dep_ == "agent":
                            out.append((str(child) + " by",'n'))
                
                if child.dep == 425 or child.dep == 412:
                    # 425 is nsubj, 412 is dobj
                    if(child.tag_ != "WP"):
                        for nchild in child.children:
                            if nchild.dep_ == "prep":
                                for pchild in nchild.children:
                                    out.append((str(child.lemma_) + " " +str(nchild) + " " + str(pchild.lemma_),'n'))
                        
                            elif nchild.dep_ == "compound":
                                out.append((str(nchild) + " " + str(child),'n'))
                        out.append((str(child.lemma_),'n'))
    
    return out

def extract_adjectives(result) :
    out = []
    for w in result:
        if (w.tag_ == 'JJ'):
            # 474a nd 477 are nouns and plural nouns
            out.append((str(w.lemma_),'jj'))
    out.reverse()
    return out

def free_nouns(result):
    # returns free nouns for a last resort test
    out=[]
    for w in result:
        if (w.tag == 474 or w.tag == 477 or w.tag_ == "attr"):
            # 474a nd 477 are nouns and plural nouns
            out.append((str(w.lemma_),'n'))
    out.reverse()
    return out


def free_verbs(result):
    # returns free verbs for a last resort test
    out=[]
    for w in result:
        if w.pos_ == "VERB" and w.lemma_!="be":
            out.append((str(w),'v'))
    out.reverse()
    return out

def test_for_what_is(line):
    if (line[0].lemma_ == 'what' or line[0].lemma_ == 'who') and line[1].lemma_== 'be' and (line[3].lemma_ == "?" or line[4].lemma_== "?"):
        return 1
    return 0

def analysis_what_is(line):
    m = re.search('(?:What|Who) (?:is|are) (.*)\?', line)
    ent = m.group(1)
    return fire_sparql_what_is(ent)

def fire_sparql_what_is(ent):
    sparqlurl = 'https://query.wikidata.org/sparql'
    url = 'https://www.wikidata.org/w/api.php'
    params = {'action': 'wbsearchentities', 'language': 'en', 'format': 'json'}
    params['search'] = ent
    json = requests.get(url, params).json()
    for result in json['search']:
        entityID = result['id']
        break;
    query = 'SELECT ?label WHERE { wd:' + entityID + ' schema:description ?label.  FILTER(LANG(?label) = "en")}'
    data = requests.get(sparqlurl,params={'query': query, 'format': 'json'}).json()
    for item in data['results']['bindings']:
        print('{}'.format(item['label']['value']) + "\t", end="")

def create_and_fire_query(line, nlp):
    
    wdapi = 'https://wikidata.org/w/api.php';
    wdparams = {'action':'wbsearchentities','language':'en', 'format':'json'}
    result = nlp(line)
    #print(result)
    
    # decide which kind of question it is
    isCountQuestion = 0
    if test_for_what_is(result):
        analysis_what_is(line)
    elif test_for_yes_no(result):
        #print("Yes question")
        simple_yes_no(result)
        # if it's a yes/no question we go have a different query
    else :
        if test_for_count(result):   
            isCountQuestion = 1
        pairs = analysis(result) # perform the keyword analysis for counting and x of y questions
        #print(pairs)
        # fires a query for each pair
        for pair in pairs:
            wdparams['search'] = pair.entity
            wdparams['type'] = 'item'
            json = requests.get(wdapi,wdparams).json()
            for result in json['search']:
                entity_id = result['id']
                wdparams['search'] = pair.relation
                wdparams['type'] = 'property'
                json = requests.get(wdapi,wdparams).json()
                
                for result in json['search']:
                    relation_id = result['id']
                    if fire_sparql(entity_id, relation_id, isCountQuestion) == 1:
                        # if it returns 1 then a solution was found so we stop
                        return 1
        if isCountQuestion == 1:
            print("3 (guess)", end='')
            return 1
        return 0

def fire_sparql(ent, rel, isCountQuestion):
    sparqlurl = 'https://query.wikidata.org/sparql'
    query = 'SELECT ?answerLabel WHERE { wd:'+ent+' wdt:'+rel+' ?answer. SERVICE wikibase:label {bd:serviceParam wikibase:language "en" .}}'
    #queries for the label of the answer not the id
    answers_found = 0 # count of answers found

    # this code is changed so that if our connection is refused for too many requests we try again after a shord wait
    data = ''
    while data == '':
        try:
            data = requests.get(sparqlurl, params = {'query':query, 'format':'json'}).json()
        except:
            #print("Connection refused by the server..")
            time.sleep(5)
            #print("Was a nice sleep, now let me continue...")
            continue
    
    for item in data['results']['bindings']:
        for key in item:
            if item[key]['type'] == 'literal':
                #prints the answer as a literal if it exists, and doesn't make exceptions for dates etc.
                if isCountQuestion == 0:
                    # only prints the answers if it isn't a count question
                    print('{}'.format(item[key]['value']) + "\t", end="")
                else:
                    possibleAnswer = item[key]['value']
                answers_found+=1 # always returns first matches (which is the right option every time I tested)
    if answers_found >= 1:
        if isCountQuestion == 1:
            if possibleAnswer.isdigit():
                print(possibleAnswer, end="")
            else:
                print(answers_found, end="")
            #should automatically format properly, because it is only one number
        return 1
    return 0

if __name__ =="__main__":
    main(sys.argv)
