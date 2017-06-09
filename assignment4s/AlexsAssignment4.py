import requests
import sys
import re
import spacy

nlp = spacy.load('en_default')

def print_example_queries():
    print("What is the milk's color?\n")
    print("Name the president of the USA?\n")
    print("Where is the capital of the Netherlands?\n")
    print("Where is Luke Skywalker's birth place?\n")
    print("Name the materials the hamburger consists of.\n")
    print("List the children of Darth Vader.\n")
    print("Where is the country of the McDonald's?\n")
    print("What is the home of Albert Heijn?\n")
    print("When is the foundation of Heineken?\n")
    print("What materials does hamburger have?\n")
    print("Give out the ingredients that the chocolate cake consists of.\n")
    print("Please input your question:")

    
def main(argv):
    print_example_queries()
    for line in sys.stdin:
        line = line.rstrip()
        result = nlp(line)
        create_and_fire_query(result)


def getNouns(result):
    phrase=[]
    relation=[]
    entity=[]
    targets=[]
    i = 0
    while i < len(result):
        if result[i].tag_=="NN" or result[i].tag_=="NNS" or result[i].tag_=="NNP":
            while result[i].dep_=="compound":
                phrase.append(result[i])
                i+=1 #fill in the first noun phrase
            if result[i].tag_=="NNS":
                phrase.append(result[i].lemma_)
            else:
                phrase.append(result[i])
            if result[i+1].tag_=="POS":
                entity = phrase
                phrase = []
            if not relation:
                relation = phrase
                phrase = []
            elif not entity:
                entity = phrase
                phrase = []
        i += 1
    targets.append(relation)
    targets.append(entity)
    return targets

        
def create_and_fire_query(result):
    api = 'http://www.wikidata.org/w/api.php'
    params = {'action':'wbsearchentities', 'language':'en', 'format':'json'}
    answers = []
    targets = getNouns(result)
    if targets[0] and targets[1]:
        relation = " ".join(str(x) for x in targets[0])
        entity = " ".join(str(x) for x in targets[1])
    else:
        print('Please give the question in the correct format.')
        return
    params['search'] = entity
    json = requests.get(api, params).json()
    for result in json['search']:
        answer = []
        entity_id = result['id']
        params['search'] = relation
        params['type'] = 'property'
        json = requests.get(api, params).json()
        for result in json['search']:
            relation_id = result['id']
            #print(relation_id)
            if not answer:
                answer.extend(fire_sparql(entity_id, relation_id))
                #answer = list(set(answer))
                break
        answers.extend(answer)
    if answers:
        answers = list(set(answers))
        for answer in answers:
                print(answer)
    else:
        print('I cannot answer this question.')


def fire_sparql(entity, relation):
    url = 'https://query.wikidata.org/sparql'
    query = 'SELECT ?answer ?answerLabel WHERE {wd:'+entity+' wdt:'+relation+' ?answer . SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }}'
    answer = []
    data = requests.get(url, params={'query': query, 'format': 'json'}).json()
    for item in data['results']['bindings']:
        for var in item:
            if 'Label' in var:
                answer.append(item[var]['value'])
    return answer
                    
                
if __name__ == "__main__":
    main(sys.argv)

