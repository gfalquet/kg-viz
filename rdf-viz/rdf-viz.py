"""Creates a .dot file that shows
- the links between classes
    if there is a triple (s p o) with (s a C) and (o a D) there is a link C -p-> D
- the ‘attributes’ of the classes
    if there is a triple (s p o) with (s a C) and o a literal then p is an attribute of C
- the prefixes of the class instances
    if we have (<http://path#xxx> a C) or (<http://path/xxx> a C) (without #) then
    <http://path#> or <http://path/> is an instance prefix of C

Use:

% python3 path-to-rdf-viz.py graph-location prefix-file

where 

graph-location is either the name of a file that contains and RDF graph
or the URL of an RDF graph stored at a SPARQL endpoint, e.g. http://localhost:7200/repositories/fds

output the .dot representation on the standard output

TODO

  - Don't show classes starting with rdf: rdfs: owl:

"""

from rdflib import Graph, Literal, RDF, URIRef, BNode
from rdflib import Namespace
from rdflib.namespace import RDF, RDFS

import sys
import re
import json

PREFIXES = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> 
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> 

"""
invprefixes = {
'http://www.openrdf.org/schema/sesame#' : 'sesame' ,
'http://www.w3.org/1999/02/22-rdf-syntax-ns#' : 'rdf' ,
'http://www.w3.org/2000/01/rdf-schema#' : 'rdfs' ,
'http://purl.org/dc/elements/1.1/' : 'dc' ,
'http://purl.org/dc/terms/' : 'dct' ,
'http://www.w3.org/2002/07/owl#' : 'owl' ,
'http://www.w3.org/2001/XMLSchema#' : 'xsd' ,
'http://www.w3.org/XML/1998/namespace' : 'xml' ,
'http://www.w3.org/2004/02/skos/core#' : 'skos' ,
 }

stdprefixes = set(['rdf','rdfs','dc','dct','owl','xsd','xml','skos'])

additional_prefix_no = 0

g = Graph()

service = ''


def prefixize(uri:str) -> str :
    global additional_prefix_no
    puri = uri
    for v in invprefixes:
        if uri.startswith(v) : return puri.replace(v, invprefixes[v]+':')

    newprefix = "p"+str(additional_prefix_no)
    pfx = extractprefix(uri)
    invprefixes[pfx] = newprefix
    additional_prefix_no += 1
    return puri.replace(pfx, newprefix+':')

def extractprefix(uri:str) -> str :
    if '#' in uri:
        return uri.split('#')[0] + '#'
    else:
        return re.sub('/[^/]+$','/', uri)

def get_one_label(class_uri: str):
    """ find one rdfs:label of class_uri 
    """
    qlab =  PREFIXES + f"""
            SELECT ?lab
            WHERE {{ 
                {service}
                {{ <{class_uri}> rdfs:label ?lab . }}
            }}
            """
    qres = g.query(qlab)
    label = ''
    for r in qres:
        print(f'// INFO // {r.lab}')
        label = r.lab
    return label

def nb_instances(class_uri: str):
    """ find the number of instances of class_uri 
    """
    qinst = f"""
            SELECT (COUNT(?i) as ?ci)
            WHERE {{ 
                {service}
                {{ ?i rdf:type <{class_uri}>. }}
            }}
            """
    qres = g.query(qinst)
    nbi = 0
    for r in qres:
        nbi = r.ci
    return f'Instances: {nbi} \\l'

def find_instance_prefixes(class_uri: str):
    """ find the prefixes of all the instances of class_uri 
    """
    qinst = f"""
            SELECT ?i
            WHERE {{ 
                {service}
                {{ ?i rdf:type <{class_uri}>. FILTER(!ISBLANK(?i))}}
            }}
            """
    qres = g.query(qinst)
    pfxset = set()
    for r in qres:
        ip = prefixize(r.i)
        pfxset.add(ip.split(':')[0])
    iplist = ''
    for pfx in pfxset:
        iplist += (pfx + "\\l")
    return iplist

def is_metaclass_name(prefixed_class_name: str):
    return prefixed_class_name.split(':')[0] in ['rdf','rdfs','owl']
       


def gen_dot_view():

    global service 

    if sys.argv[1].startswith('http://'):
        service = f'SERVICE <{sys.argv[1]}> '
    else:
        g.parse(sys.argv[1])

    # load additional prefixes

    if len(sys.argv) > 2:
        f = open(sys.argv[2])
        content = f.read()
        prefixes = json.loads(content)
        for p in prefixes:
            invprefixes[prefixes[p]] = p

    # Find the classes, excluding the metaclasses 
    # and create a dictionary prefixed-class -> URI

    qc =  f"""
                SELECT DISTINCT ?c
                WHERE {{
                    {service}
                    {{ ?x rdf:type ?c.  FILTER(! ISBLANK(?c) )
                    }}
                }}
                """
    qcres = g.query(qc) 
    classes = {}
    for r in qcres:
        c = prefixize(r.c)
        if not is_metaclass_name(c):
            classes[c] = r.c

    print("""
    digraph g {
        node [shape = record, fontname = "Helvetica"] ;
    """)

    # Find the class links

    print('\n### Class link\n')

    qref =  f"""
                SELECT DISTINCT ?x ?p ?z
                WHERE {{
                    {service}
                    {{ ?s rdf:type ?x. ?o rdf:type ?z . ?s ?p ?o.  FILTER(! ISBLANK(?z) )
                }}
                }}
                """
    qrefres = g.query(qref) 

    clsloop = {}
    for r in qrefres:
        n1 = prefixize(r.x)
        n2 = prefixize(r.z)
        lab = prefixize(r.p)
        if not is_metaclass_name(n1) and not is_metaclass_name(n2):
            if n1 == n2 :
                clsloop[n1] = clsloop[n1] + '\n' + lab if n1 in clsloop else lab
            else:
                print(f'  "{n1}" -> "{n2}" [label = "{lab}"] ;')

    for c in clsloop:
        print(f'  "{c}" -> "{c}" [label = "{clsloop[c]}"] ;')


    print('\n### Class attributes, instances, instance prefixes\n')
    # Class attributes

    for c in classes:

        name = c
        l = get_one_label(classes[c])
        if l != '':
            name = name +"\\n"+l

        qref =  f"""
                    SELECT DISTINCT ?x ?p 
                    WHERE {{ 
                        {service}
                        {{ ?s rdf:type <{classes[c]}>. ?s ?p ?o.  FILTER(ISLITERAL(?o) ) }}
                    }}
                    """
        qrefres = g.query(qref)

        attributes = ""
        for r in qrefres:
            attributes += (prefixize(r.p)) + "\\l"

        nb_inst = nb_instances(classes[c])
        instance_pfx = find_instance_prefixes(classes[c])

        print(f'"{c}" [label="{{{name} |{attributes}|{nb_inst}|{instance_pfx}}}"] ;')

    print("""subgraph {
    node [color="white"]
    """)

    prefixes = {}
    for ip in invprefixes:
        prefixes[invprefixes[ip]] = ip

    print('\n### Prefixes\n')

    label = '"{Prefixes:|\\l'
    for p in sorted(prefixes.keys()):
        if p not in stdprefixes:
            label += f"{p}: {prefixes[p]}\\l"
    label += '}"'
    print(f'prefs[label={label}];')

    print("}}")

if __name__ == "__main__":
    gen_dot_view()

