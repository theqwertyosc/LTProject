import sys
import requests
import re
import spacy
import collections
import csv
import time


def main(argv):
    nlp = spacy.load('en_default') #put this first so we don't load it for every question
    #print_example_queries()
    
    questionCount = 0
    for line in sys.stdin:
        line = line.rstrip() # removes newline

        splitLine = line.split("\t")
        if len(splitLine)>=2:
            line = splitLine[1]
            print(splitLine[0] + "\t", end="")
        else: #question withoutnumber
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


def analysis_yes_no(line) :
    # TODO: write this function
    # not sure the best way to do this, but can probably use some of the
    # helper functions for the normal analysis
    wdapi = 'https://wikidata.org/w/api.php';
    wdparams = {'action':'wbsearchentities','language':'en', 'format':'json'}
    phrase = ""
    entity1 = ""
    entity2 = ""
    rel = ""
    i = 0
    while i < len(line):
        if line[i].tag_ == "NN" or line[i].tag_ == "NNS" or line[i].tag_ == "NNP":
            while line[i].dep_ == "compound":
                phrase += str(line[i]) + " "
                i+=1 #fill in the first noun phrase
            if line[i].tag_ == "NNS":
                phrase += str(line[i].lemma_)
            else:
                phrase += str(line[i])
            if entity1 == "":
                entity1 += phrase
                phrase = ""
            elif entity2 == "":
                entity2 += phrase
                phrase = ""
            elif entity2 != "":
                entity2 += " " + phrase
                phrase = ""
        elif line[i].tag_ == "JJ" and entity2 == "":
            entity2 += str(line[i])
        elif line[i].tag_ == "VB":
            rel += str(line[i].lemma_)
        i += 1
    return fire_sparql_yes_no(entity1, rel, entity2)

#return fire_sparql_yes_no(ob1, rel, ob2)

def answer_yes_no(ob1, rel, ob2):
    url = 'https://query.wikidata.org/sparql'
    query = 'ASK {wd:'+ob1+' wdt:'+rel+' wd:'+ob2+'.}'
    result = requests.get(url, params={'query': query, 'format': 'json'}).json()
    if result['boolean'] == True:
        answer = 'Yes'
    elif result['boolean'] == False:
        answer = 'No'
    print(answer)


def fire_sparql_yes_no(ob1, rel, ob2) :
    # Searches for the relationship between two objects
    # Returns booleans
    entity1_id = ""
    entity2_id = ""
    url = 'https://query.wikidata.org/sparql'
    wdapi = 'https://wikidata.org/w/api.php';
    wdparams = {'action':'wbsearchentities','language':'en', 'format':'json'}
    
    wdparams['search'] = ob1
    wdparams['type'] = 'item'
    json = requests.get(wdapi, wdparams).json()
    for result in json['search']:
        entity1_id = result['id']
        wdparams['search'] = ob2
        wdparams['type'] = 'item'
        json = requests.get(wdapi, wdparams).json()
        for result in json['search']:
            entity2_id = result['id']
            if rel == "":
                query = 'SELECT ?relation ?relationLabel WHERE {wd:'+entity1_id+' ?relation wd:'+entity2_id+' . SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }}'
                data = requests.get(url, params={'query': query, 'format': 'json'}).json()
                for item in data['results']['bindings']:
                    for key in item:
                        if item[key]['type'] == 'literal':
                            wdparams['search'] = ('{}'.format(item[key]['value']))
                            wdparams['type'] = 'property'
                            json = requests.get(wdapi,wdparams).json()
                            for searchResult in json['search']:
                                rel = searchResult['id']
                                return answer_yes_no(entity1_id, rel, entity2_id)
            else:
                wdparams['search'] = rel
                wdparams['type'] = 'property'
                json = requests.get(wdapi,wdparams).json()
                for result in json['search']:
                    rel = result['id']
                    return answer_yes_no(entity1_id, rel, entity2_id)
    print("I don\'t know the answer")


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
    entList.extend(free_nouns(line, relList))
    relList.extend(free_verbs(line))
    relList.extend(free_nouns(line, relList))
    entList.extend(free_verbs(line))

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

    Pair =collections.namedtuple('Pair',['entity','relation'])
    for ent in ent_sorted:
        for rel in rel_sorted:
            if ent != rel:
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


def free_nouns(result, relList):
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
            out.append((str(w.lemma_),'v'))
    out.reverse()
    return out

def create_and_fire_query(line, nlp):
    
    wdapi = 'https://wikidata.org/w/api.php';
    wdparams = {'action':'wbsearchentities','language':'en', 'format':'json'}
    result = nlp(line)
    #print(result)
    
    # decide which kind of question it is
    isCountQuestion = 0
    if test_for_yes_no(result):
        #print("Yes question")
        analysis_yes_no(result)
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
        return 0

def fire_sparql(ent, rel, isCountQuestion):
    sparqlurl = 'https://query.wikidata.org/sparql'
    query = 'SELECT ?answerLabel WHERE { wd:'+ent+' wdt:'+rel+' ?answer. SERVICE wikibase:label {bd:serviceParam wikibase:language "en" .}}'
    #queries for the label of the answer not the id
    answers_found = 0 # count of answers found
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
                print(possibleAnswer)
            else:
                print(answers_found)
            #should automatically format properly, because it is only one number
        return 1
    return 0

if __name__ =="__main__":
    main(sys.argv)
