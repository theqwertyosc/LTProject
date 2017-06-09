import requests
import sys
import re
import spacy
import collections
def main(argv):
    nlp = spacy.load('en_default')
    print_example_queries()
    
    for line in sys.stdin:
        line = line.rstrip() # removes newline
        answer = create_and_fire_query(line, nlp)
        if answer == 0:
            print("No answer found")
        #end of file ends program because stdin is used

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
                    out.append(ent)
                    ent = ""
                started = 1
            ent += str(w) #w.lemma_ also a poss
        elif started == 1:
            started = 0
            out.append(ent)
            ent = ""
    if started ==1:
        out.append(ent)        
    return out


def extract_subj(result):
    # returns every nsubj  of every verb
    out =[]
    for w in result:
        if w.pos == 98:
            # 98 is VERB
            for child in w.children:
                if child.dep_ == "auxpass":
                    for achild in child.children:
                        if achild.dep_ == "agent":
                            out.append(str(child) + " by")
                
                if child.dep == 425 or child.dep == 412:
                    # 425 is nsubj, 412 is dobj
                    if(child.tag_ != "WP"):
                        for nchild in child.children:
                            if nchild.dep_ == "prep":
                                for pchild in nchild.children:
                                    out.append(str(child.lemma_) + " " +str(nchild) + " " + str(pchild.lemma_))
                        
                            elif nchild.dep_ == "compound":
                                out.append(str(nchild) + " " + str(child))
                        out.append(str(child.lemma_))
    
    return out


def free_nouns(result, relList):
    out=[]
    for w in result:
        if (w.tag == 474 or w.tag == 477 or w.tag_ == "attr") and relList.count(str(w.lemma_)) == 0:
            # 474a nd 477 are nouns and plural nouns
            out.append(str(w.lemma_))
    out.reverse()
    return out


def free_verbs(result):
    out=[]
    for w in result:
        if w.pos_ == "VERB" and w.lemma_!="be":
            out.append(str(w))
    out.reverse()
    return out


        
def analysis(line, nlp):
    result = nlp(line)
    entList = []
    relList = []
    pairs = []
    # Strategy is to have two lists, one of entities and
    # one of relations, compiled so that most reliable options are
    # earlier in the list. Then cycle throught the
    # combinations until there is an answer.
    entList.extend(extract_named_entities(result))

    relList.extend(extract_subj(result))

    entList.extend(free_nouns(result, relList))

    relList.extend(free_verbs(result))

    Pair =collections.namedtuple('Pair',['entity','relation'])
    for ent in entList:
        for rel in relList:
            pairs.append(Pair(str(ent),str(rel)))
    return pairs


    

def print_example_queries():
    print("List the ingredients of a pizza.")
    
    
    print("Who is Heinz owned by?")
    
    
    print("What are Jamie Oliver's jobs?")
    
    
    print("When was Cadbury founded?")
    
    
    print("What's the fabrication method of a biscuit?")
    # fabrication/manufacturing/production method
    
    print("What shape is a stroopwafel?")
    #
    
    print("What is Wensleydale Cheese named after?")
    # etymology or toponym give the same result
    
    print("What's Ainsley Harriott's gender?")
    # gender or sex, name doesnt need to be capitalised
    
    print("What is the country of origin of the croissant?")
    # "country of origin", "place of origin", "origin" or "origin country"
    
    print("What are the possible colours of an apple?\n\n Ask your question(s):\n")
    #accepts colour and color


def create_and_fire_query(line, nlp):
    wdapi = 'https://wikidata.org/w/api.php';
    wdparams = {'action':'wbsearchentities','language':'en', 'format':'json'}
    # This template is general, and can also be used for other topics, eg "Who are the spouses of John Lennon?"
    ###template = re.compile('(?:[wW]hat|[wW]ho)(?: is| are|\'s)(?: the| an| a)? (.*) of(?: the| an| a)? (.*)\\?')
    ## Accepts:
    #What/what/Who/who is/are/'s the/an/a/ (relation) of the/an/a/ (entity)?
    #Searching lets you ask the same relation in multiple ways, eg CEO, ceo, chief exectuive, chief executive officer
    ###m = re.match(template,line)
    #if m == None:
    #    print("Invalid input format, try again.")
    #    return -1
    #relation = m.group(1)
    #if relation.endswith('s'):
        # Leaving off a final 's' allows the properties to be expressed as plurals, and I could not think
        # of a situation where this would prevent a relation from being found. If this was an issue,
        # then the "s" could be left on, but then relations would have to be singular.
    #    relation = relation[:-1]                         
    #entity = m.group(2)
    # print(entity+ " " +relation)
    
    pairs = analysis(line, nlp)

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
                if fire_sparql(entity_id, relation_id) == 1:
                    # if it returns 1 then a solution was found so we stop
                    return 1
    return 0


def fire_sparql(ent,rel):
    sparqlurl = 'https://query.wikidata.org/sparql'
    query = 'SELECT ?answerLabel WHERE { wd:'+ent+' wdt:'+rel+' ?answer. SERVICE wikibase:label {bd:serviceParam wikibase:language "en" .}}'
    #queries for the label of the answer not the id
    answer_found = 0
    data = requests.get(sparqlurl, params = {'query':query, 'format':'json'}).json()
    for item in data['results']['bindings']:
        for key in item:
            if item[key]['type'] == 'literal':
                #prints the answer as a literal if it exists, and doesn't make exceptions for dates etc.
                print('{}'.format(item[key]['value']))
                answer_found = 1 # always returns first matches (which is the right option every time I tested)
    if answer_found == 1:
        return 1
    return 0
            

if __name__ =="__main__":
    main(sys.argv)
