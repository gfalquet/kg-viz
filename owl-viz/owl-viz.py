""" 



transformation algo

x rdf:type owl:Restriction ;
  owl:onProperty y ;
  owl:someValuesFrom z ;  // allVAluesFrom
---->
x [shape="rectangle",color="orange",label="∃ y", height=0.1];
x -> z ;





"""

from rdflib import Graph, Literal, RDF, URIRef, BNode
from rdflib import Namespace
from rdflib.namespace import RDF, RDFS

#from titre_date import xdate

import sys
import re

np = Namespace("http://unige.ch/rcnum/")
g = Graph()
g.parse(sys.argv[1])
# g.bind('e', ne)
g.bind('', np)
g.bind('rdf', RDF)


def suffix(x: str):
    return re.sub(r'.*(#|/)','', x).replace('-','_')

dotnodelabel = {}   ## node IRI to dot node name

print('digraph {')
print('  rankdir="BT"')

# IRI classes


q_iri_classes = f"""
    SELECT DISTINCT ?x ?label
    WHERE {{ {{ {{?x rdf:type owl:Class}} 
                UNION 
                {{?y rdfs:subClassOf|owl:equivalentClass|rdf:type ?x}} }} 
              OPTIONAL {{ ?x rdfs:label ?label}}
              FILTER(! ISBLANK(?x))
            }}
"""
qres = g.query(q_iri_classes)
for r in qres:
    name = suffix(r.x)
    if r.label != None:
        name = r.label
    dotnodelabel[r.x] = '{'+name+'|}'
    # del # print(f"""   "{r.x}" [label="{name}"] ;""")

## Add the attributes = 

# subClassOf -> DatatypeProptery SOME/ONLY C
# subClassOf -> property SOME/ONLY Datatype

restrictionOnDatatype = set()

for op in ["owl:someValuesFrom", "owl:allValuesFrom", "owl:maxCardinality", "owl:minCardinality", "owl:maxQualifiedCardinality", "owl:minQualifiedCardinality"]:
    q = f"""
                SELECT DISTINCT ?x ?p ?y ?rstr
                WHERE {{ ?x rdfs:subClassOf ?rstr .
                         ?rstr rdf:type owl:Restriction ;  {op} ?y ;  owl:onProperty ?p .
                         {{
                            {{?p rdf:type owl:DatatypeProperty}}
                            UNION
                            {{?rstr {op} ?y FILTER(STRSTARTS(STR(?y), "http://www.w3.org/2001/XMLSchema#"))}}
                         }}
                }}
    """ 
    qres = g.query(q)
    for r in qres:
        name = dotnodelabel[r.x]
        if name[-2:] == '|}':
            dotnodelabel[r.x] = re.sub(r'}', suffix(r.p) + ': ' + suffix(r.y) + '}', name)
        else: 
            dotnodelabel[r.x] = re.sub(r'}', '\\\\n' + suffix(r.p)  + ': ' + suffix(r.y) + '}', name) 

        restrictionOnDatatype.add(r.rstr)

for nid in dotnodelabel:
    print(f"""   "{nid}" [shape="record",label="{dotnodelabel[nid]}"] ;""")

# AND and OR

for op in ["owl:unionOf", "owl:intersectionOf"]:
    q_and_or_classes = f"""
                SELECT DISTINCT ?x  
                WHERE {{ ?x {op} ?y
                }}
    """
    qres = g.query(q_and_or_classes)
    for r in qres:
        if op == "owl:unionOf":
            name = "OR"
        else:
            name = "AND"
        dotnodelabel[r.x] = name
        print(f"""   "{r.x}" [label="{name}", shape="rectangle", color="green"] ;""")
# arguments
qa = f"""
            SELECT DISTINCT ?x ?c
            WHERE {{?x (owl:unionOf|owl:intersectionOf)/rdf:rest*/rdf:first ?c
                FILTER NOT EXISTS{{?c rdf:type owl:Restriction}} }}
        """
qares = g.query(qa)
for ra in qares:
        print(f"""   "{ra.x}" -> "{ra.c}" """)

# SOME and ONLY on object property -> [node]

for op in ["owl:someValuesFrom", "owl:allValuesFrom", "owl:maxCardinality", "owl:minCardinality", "owl:maxQualifiedCardinality", "owl:minQualifiedCardinality"]:
    q_restriction = f"""
                SELECT DISTINCT ?x  ?p  ?y ?rst ?c
                WHERE {{ ?x rdfs:subClassOf|((owl:unionOf|owl:intersectionOf)/rdf:rest*/rdf:first) ?rst . 
                         ?rst rdf:type owl:Restriction ;  {op} ?y ;  owl:onProperty ?p .
                         OPTIONAL{{?rst owl:onClass ?c}}
                }}
    """ 
    qres = g.query(q_restriction)
    for r in qres:
        if r.rst not in restrictionOnDatatype:
            target = r.y
            name = suffix(r.p)
            print(f"// {op} {name} {r.y}")
            if op == "owl:someValuesFrom":
                name = "∃ " + name
            elif op == "owl:maxCardinality":
                name = "≤ " + r.y + name
                target = "owl:Thing"
            elif op == "owl:minCardinality":
                name = "≥ " + r.y + name
                target = "owl:Thing"
            elif op == "owl:maxQualifiedCardinality":
                name = "≤ " + r.y + name
                target = r.c
            elif op == "owl:minQualifiedCardinality":
                name = "≥ " + r.y + name
                target = r.c
            else:
                name = "∀ " + name
            dotnodelabel[r.x] = name
            print(f""" "{r.x}" -> "{target}" [label="{name}"]""")
            # print(f"""   "{r.x}" [label="{name}", shape="rectangle",color="orange"] ;""")
# print(dotnode)


# Subclasses

qref =  f"""
            SELECT DISTINCT ?x ?y 
            WHERE {{ ?x rdfs:subClassOf ?y 
                    FILTER NOT EXISTS{{?y rdf:type owl:Restriction}}
            }}
            """
qrefres = g.query(qref)

for r in qrefres:
    if r.y not in restrictionOnDatatype:
        print(f'  "{r.x}" -> "{r.y}" [ arrowhead="onormal"]; ')

# Equivalent Classes


qref =  f"""
            SELECT DISTINCT ?x ?y 
            WHERE {{ ?x owl:equivalentClass ?y 
            }}
            """
qrefres = g.query(qref)

for r in qrefres:
    if r.y not in restrictionOnDatatype:
        print(f'  "{r.x}" -> "{r.y}" [ dir="both", color="black:black", arrowhead="onormal", arrowtail="onormal"]; ')



print('}')
