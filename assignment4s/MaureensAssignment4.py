import sys
import requests
import re
import json
import spacy


def main(argv):
	print_example_queries();
	for line in sys.stdin:
		if line =='quit\n':
			sys.exit()
		line = line.rstrip()
		answer = create_and_fire_query(line)
		print('Next question please: (enter "quit" to exit)\n')


def print_example_queries():
	print("These are example questions I can answer:\n")
	print("What is the color of an apple?")
	print("List the colors of an apple.")
	print("When was the inception of Heinz?")
	print("What is the country of origin of bratwurst?")
	print("What is the opposite of herbivore?")
	print("Give the opposite of a carnivore.")
	print("What is the main food sourse of koala?")
	print("What is the ingredient of chocolate?")
	print("List the ingredients of chocolate.")
	print("\n Ask your question\n")


def parse_question(line):
	nlp = spacy.load('en_default')
	result = nlp(line)
	subj = []
	obj = []
	namedEntity = []
	for w in result:
		if w.dep_=="nsubj" or w.dep_=="dobj":
			subj = w.lemma_
		if w.dep_=="pobj":
			obj = w.lemma_
	entities = [subj,obj]
	return entities 


def create_and_fire_query(line) :
	wdapi = 'https://www.wikidata.org/w/api.php'
	wdparams = {'action':'wbsearchentities','language':'en','format':'json'}


        

        
	entities = parse_question(line)
	entity = str(entities[1])
	relation = str(entities[0])
	wdparams['search'] = entity
	json = requests.get(wdapi,params=wdparams).json()
	for result in json['search']:
		entity_ID = result['id']
		wdparams['search'] = relation
		wdparams['type'] = 'property'
		json = requests.get(wdapi,params=wdparams).json()
		for result in json['search']:
			relation_ID = result['id']
			fire_sparql(entity_ID,relation_ID)

 
def fire_sparql(ent,rel):
	sparqlurl = 'https://query.wikidata.org/sparql'
	query = 'SELECT ?itemLabel WHERE { wd:'+ent+' wdt:'+rel+' ?item. SERVICE wikibase:label {bd:serviceParam wikibase:language "en".}}'
	data = requests.get(sparqlurl, params={'query': query, 'format': 'json'}).json() 
	for item in data['results']['bindings']:
		for key in item :
			if len(item[key]['value']) == 0:
				print('Sorry, I could not find an answer')
			else:
				print('{}'.format(item[key]['value']))


if __name__ == '__main__':
    main(sys.argv)
			
