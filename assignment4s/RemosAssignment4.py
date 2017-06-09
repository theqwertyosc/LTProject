#! /usr/bin/python

# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.
import sys
import requests
import re
import spacy

def print_example_queries():
    print("What is Gordon Ramsey's birth date?")
    print("What is the material used in milkshake?")
    print("Give the colour of apple.")
    print("What is wine's ingredient?")
    print("Who is the founder of Burger King?")
    print("How many employees does Taco Bell have?")
    print("Give pasta's origin.")
    print("What is the source country of fries?")
    print("Who is the owner of KFC?")
    print("Give veganism's corresponding movement")
    print("Who is the manufacturer of Big Mac?")
    print("\n")



def main(argv):
    print_example_queries()
    global answered
    while(1):
        answered = 0
        print("\nAsk your question or give your command:")
        line1 = input()
        if not line1:
            sys.exit(0)
        create_and_fire_query(line1)
        if answered != 1:
            print("Could not find an answer.")

def create_and_fire_query(line)	:    
	nlp = spacy.load('en_default')
	result = nlp(line)
	for w in result	:
		#get property
		if w.head.pos_ == "VERB" and w.pos_ == "NOUN":
			subject = w.text
		#get entity
		if (w.dep_ == "pobj" or w.dep_ == "poss"):
			obj = []
			for d in w.subtree:
				if d.pos_ == "PROPN" or d.pos_ == "NOUN":
					obj.append(d.text)	
	
	prop = subject
	entity = " ".join(obj)
	#Get entity and property ID
	url = 'https://www.wikidata.org/w/api.php'
	params = {'action':'wbsearchentities', 'language':'en', 'format':'json'}
	params['search'] = entity
	json = requests.get(url,params).json()
	for result in json['search']:
		entityID = result['id']
		params['search'] = prop
		params['type'] = 'property'
		json = requests.get(url,params).json()
		for result in json['search']:
			propertyID = result['id']
			x = fire_sparql(entityID, propertyID)
			if x == 0:
				break
		break
        
sparqlURL = 'https://query.wikidata.org/sparql'

def fire_sparql(ent, prop):
    global answered
    query='''
SELECT ?answer ?answerLabel
WHERE
{
	wd:'''+ ent +''' wdt:''' + prop + ''' ?answer .
	SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
'''
    data = requests.get(sparqlURL,params={'query': query, 'format': 'json'}).json()
    for item in data['results']['bindings']:
        category = item['answerLabel']['value']
        print(category) 
        answered = 1
    
if __name__ == "__main__":
    main(sys.argv);


