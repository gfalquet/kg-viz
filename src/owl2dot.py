""" Create a graphical representation in .dot of an OWL ontology

Limitations:
- individuals are not represented
- most of the property axioms (RBox) are not represented (domains/ranges are represented)
- 

v. 2025-10-10

typical use : python3 path-to-owl2dot.py  path-to-owl-file | dot -Tpdf  -o path-to-graph-view-file.pdf

"""


from rdflib import Graph, Literal, URIRef, BNode
from rdflib import Namespace
from rdflib.namespace import RDF, RDFS, OWL
from rdflib.term import Node

import sys
import re

from dataclasses import dataclass

SUBCLASS_LINK_COLOR = "orange"
RESTR_LINK_COLOR = "blue"
DOM_RNG_LINK_COLOR = "#008800"
ARG_LINK_COLOR = "magenta"

@dataclass
class DotNode:
    classname: str = ''
    attributes: str = ''
    annotations: str = ''
    isPropRestr: bool = False
    isAnnotVal: bool = False
    isAndOrNot: bool = False


annot_flag = '--annot' in sys.argv
alc_flag = '--alc' in sys.argv

np = Namespace("http://unige.ch/rcnum/")
np = Namespace("http://humanbehaviourchange.org/ontology/")
g = Graph()
g.parse(sys.argv[1])
# g.bind('e', ne)
g.bind('', np)
#g.bind('rdf', RDF)

def makelabel(g: Graph, x: Node) -> str:
    if type(x) == BNode : return '{BN}'
    res = get_preferred_label(g, x)
    if res == '' : res = suffix(x)
    return res


def get_preferred_label(graph: Graph, subject: URIRef) -> str:
    # subject = URIRef(iri)
    labels = list(graph.objects(subject, RDFS.label))
    if not labels:
        return ""
    
    # Try to find a label without a language tag
    for label in labels:
        if isinstance(label, Literal) and label.language is None:
            return str(label)
    
    # Try to find a label with 'en' language tag
    for label in labels:
        if isinstance(label, Literal) and label.language == 'en':
            return str(label)
    
    # Return any label
    return str(labels[0]) if labels else ""

def suffix(x: str):
    return re.sub(r'.*(#|/)','', x).replace('-','_')


def genObjRestr(g: Graph, nodeLabels : dict[Node, DotNode], visibleNodes: set[Node]):
    """ 
    Represent restrictions on object properties

    A restriction R <restriction> D is represented as

            ┌────┐     <restriction> R     ┌─────┐
            │    │ ----------------------> │  D  │
            └────┘                         └─────┘

    If the restriction is a superclass there is a shortcut : C ⊑ R <restriction> D is represented as

                ┌────┐     <restriction> R     ┌─────┐
                │ C  │ ----------------------> │  D  │
                └────┘                         └─────┘

    The same shortcut is applied to Union/Intersection : A1 union R <restriction> D ... =>

                ┌────┐           ┌────┐     <restriction> R     ┌─────┐
                │ A1 │ <-------- │ OR │ ----------------------> │  D  │
                └────┘           └────┘                         └─────┘

    """
    # restrictions on object properties
    # SOME and ONLY on object property -> [node]
    args = set()
    objrestr = set()
    subc = set()
    print('''
    
    // Restrictions
    
    ''')
    optSc = """?x rdfs:subClassOf ?rst"""
    optArg = """?x (owl:unionOf|owl:intersectionOf)/rdf:rest* ?arg. ?arg rdf:first ?rst"""
    optOther = """{{ {{ ?z ?someLinkTo ?rst }} UNION {{ ?rst rdfs:subClassOf|owl:equivalenClass ?z}} }}"""

    loopNo = 0
    for shortcut in [optSc, optArg, optOther]:
        for op in ["owl:someValuesFrom", "owl:allValuesFrom", 
                "owl:cardinality", "owl:maxCardinality", "owl:minCardinality", 
                "owl:qualifiedCardinality", "owl:maxQualifiedCardinality", "owl:minQualifiedCardinality",
                "owl:hasValue"]:
            q_restriction = f"""
                        SELECT DISTINCT ?x ?rst ?p ?y ?c ?arg
                        WHERE {{
                                ?rst rdf:type owl:Restriction ;  owl:onProperty ?p  ; {op} ?y .    
                                ?p rdf:type owl:ObjectProperty .
                                OPTIONAL {{?rst owl:onClass ?c}}
                                {shortcut}
                        }}
            """ 
            qres = g.query(q_restriction)
            for r in qres:
                target = r.y
                arclabel = makelabel(g, r.p)
                print(f"// {op} {arclabel} {r.y}")
                if op == "owl:someValuesFrom":
                    # ALT arclabel = '∃ ' + arclabel
                    arclabel = f''' ∃ <B>{arclabel}</B>''' if alc_flag else f'''<B>  {arclabel}</B>  some'''
                elif op == "owl:allValuesFrom":
                    # ALT arclabel = '∀ ' + arclabel
                    arclabel = f''' ∀ <B>{arclabel}</B>''' if alc_flag else f'''<B>  {arclabel}</B> only'''
                elif op == "owl:cardinality":
                    target = "owl:Thing"
                    arclabel = "= " + r.y + ' ' + arclabel
                elif op == "owl:maxCardinality":
                    target = "owl:Thing"
                    arclabel = "≤ " + r.y + ' ' + arclabel
                elif op == "owl:minCardinality":
                    target = "owl:Thing"
                    arclabel = "≥ " + r.y  + ' ' + arclabel              
                elif op == "owl:qualifiedCardinality":
                    arclabel = "= " + r.y + ' ' + arclabel
                    target = r.c
                elif op == "owl:maxQualifiedCardinality":
                    arclabel = "≤ " + r.y + ' ' + arclabel
                    target = r.c
                elif op == "owl:minQualifiedCardinality":
                    arclabel = "≥ " + r.y + ' ' + arclabel
                    target = r.c
                elif op == "owl:hasValue":
                    arclabel = arclabel + " (has value)" 
                    target = r.y
                else:
                    arclabel = "** ERROR **"

                if shortcut == optSc:
                    if target == r.x : # loop
                        loopNo += 1
                        #intermediateNode = f"X-inter-loop-{loopNo}"
                        #print(f""" "{r.x}" -> "{intermediateNode}":e [color = "blue" label=<{arclabel}>] ; // shortcut 1""")
                        #print(f""" "{intermediateNode}":w -> "{r.x}" [color = "blue"]; """)
                        #print(f""" "{intermediateNode}" [label=" ", width=0.25, height=0.25] ; """)
                        print(f""" "{r.x}":n -> "{target}":s [color = "{RESTR_LINK_COLOR}", label=<{arclabel}>] // shortcut 1""")
                    else:
                        print(f""" "{r.x}" -> "{target}" [color = "{RESTR_LINK_COLOR}", label=<{arclabel}>] // shortcut 1""")
                    visibleNodes.add(r.x)
                    visibleNodes.add(target)
                    g.remove((r.x, RDFS.subClassOf, r.rst))
                    # print(f'''///// removed {(r.x, RDFS.subClassOf, r.rst)}''')
                elif shortcut == optArg:
                    print(f""" "{r.x}" -> "{target}" [color = "{RESTR_LINK_COLOR}", label=<{arclabel}>] // shortcut 1""")
                    visibleNodes.add(r.x)
                    visibleNodes.add(target)
                    g.remove((r.arg, RDF.first, r.rst))
                else:    
                    print(f""" "{r.rst}" -> "{target}" [color = "black" label=<{arclabel}>]""")           
                    nodeLabels[r.rst] = DotNode(isPropRestr=True) #'PROP_RESTR#'+suffix(r.p)  # This is to indicate that this node represents a property restriction
                    objrestr.add(r.rst)
                    visibleNodes.add(r.rst)
                    visibleNodes.add(target)

                # args.add(target)

            
            
    return (objrestr, args, subc)

def genDatatypeRestr(g: Graph, nodeLabels: dict[Node,DotNode], visibleNodes: set[Node]) -> set[str]:
    """ 
    Represents datatype restrictions as lines in the class node label

    C ⊑ R Θ DType  (where either R is a dt property or DType is data class)
    ---> 
        _____________
        | C          |
        |------------|
        | R : DType  |
    """
    print("""
    
    /// Datatype Property Restrictions -> Attributes
    
    """)
    restrictionOnDatatype = set() 
    q = f"""
                SELECT DISTINCT ?x ?p ?y ?rstr
                WHERE {{ ?x rdfs:subClassOf ?rstr .
                        ?rstr rdf:type owl:Restriction ;  owl:onProperty ?p .
                        {{ 
                            ?p rdf:type owl:DatatypeProperty . ?rstr owl:someValuesFrom|owl:allValuesFrom|owl:onDataRange ?y
                        }}
                        UNION
                        {{ 
                            ?rstr owl:someValuesFrom|owl:allValuesFrom|owl:onDataRange ?y FILTER(STRSTARTS(STR(?y), "http://www.w3.org/2001/XMLSchema#"))
                        }}
                        UNION # no class qualification
                        {{
                            ?rstr owl:cardinality|owl:maxCardinality|owl:minCardinality ?card. ?p rdf:type owl:DatatypeProperty .  BIND("owl:Thing" AS ?y)
                        }}
                }}
    """ 
    qres = g.query(q)
    for r in qres:
        print(f"""// subclass of restriction on datatype {r.x} {r.p} {r.y}""")
        if True: #r.x in objRestrArg or r.x in andOrNotArg or r.x in subc or r.x in eqc:
            if r.x not in nodeLabels : 
                nodeLabels[r.x] = DotNode(classname=makelabel(g, r.x))
                visibleNodes.add(r.x)
            dotnode = nodeLabels[r.x]
            name = dotnode.classname
            #del if name[-1] != '}' : name = '{' + name + '|}'
            dotnode.attributes += suffix(r.p) + ': ' + suffix(r.y) + '\\l' 
            restrictionOnDatatype.add(r.rstr)
    return restrictionOnDatatype

def genDomRng(g: Graph, nodeLabels : dict[Node, DotNode], visibleNodes: set[Node]):
    """
    Property with domain and/or range representation

    """
    print("""
    
    /// Domains and Ranges
    
    """)
    qdomrng = f"""
                SELECT DISTINCT ?dom ?rng 
                    #(GROUP_CONCAT(REPLACE(REPLACE(STR(?p), ".*/", ""), ".*#", "") ; separator="<br/>") AS ?props)
                    (GROUP_CONCAT(STR(?p) ; separator="<br/>") AS ?props)
                WHERE {{ ?p rdf:type owl:ObjectProperty .
                    OPTIONAL {{
                        ?p rdfs:domain ?dom
                    }}
                    OPTIONAL {{
                        ?p rdfs:range ?rng
                    }}
                }}
                GROUP BY ?dom ?rng
                """
    qres = g.query(qdomrng)
    nid = 0
    for r in qres :
        if r.dom != None or r.rng != None :
            if r.dom == None or r.rng == None :
                nodeid = "https://white-placeholder/"+str(nid)
                nid += 1
                nodeLabels[nodeid] = DotNode(classname="*")
                visibleNodes.add(nodeid)
            else:
                nodeid = None # never used
            source = r.dom if r.dom != None else nodeid
            target = r.rng if r.rng != None else nodeid
            if r.dom != None : 
                if r.dom not in nodeLabels : nodeLabels[r.dom] = DotNode(classname=makelabel(g, r.dom))
                visibleNodes.add(r.dom)
            if r.rng != None :
                if r.rng not in nodeLabels : nodeLabels[r.rng] = DotNode(classname=makelabel(g, r.rng))
                visibleNodes.add(r.rng)
            proplabels = "<br/>".join(list(map(lambda x : makelabel(g, URIRef(x)), r.props.split('<br/>'))))
            if source == target: # loop
                print(f'  "{source}":n -> "{target}":s [  color="{DOM_RNG_LINK_COLOR}", label=<<b>{proplabels}</b>>]')      #{makelabel(g, r.p)}"]; ')
            else:
                print(f'  "{source}" -> "{target}" [  color="{DOM_RNG_LINK_COLOR}", label=<<b>{proplabels}</b>>]; ')

  

def genAndOr(g: Graph, nodeLabels : dict[Node, DotNode], visibleNodes: set[Node], opShortcuts: set[Node]) -> tuple[set[Node], set[Node]]:
    andornot = set()
    andornotarg = set()
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
            nodeLabels[r.x] = DotNode(classname=name, isAndOrNot=True)
            andornot.add(r.x)
            visibleNodes.add(r.x)
        
            print(f"""   "{r.x}" [label="{name}", shape="rectangle", height="0", style="rounded", margin="0.02,0.02", color="black"] ;""")
    # arguments
    qa = f"""
                SELECT DISTINCT ?x ?c
                WHERE {{?x (owl:unionOf|owl:intersectionOf)/rdf:rest*/rdf:first ?c
                    # FILTER NOT EXISTS{{?c rdf:type owl:Restriction}} 
                }}
            """
    qares = g.query(qa)
    for ra in qares:
            if (ra.x, ra.c) not in opShortcuts:
                print(f"""   "{ra.x}" -> "{ra.c}" [ color="{ARG_LINK_COLOR}"]""")
                andornot.add(ra.x)
                andornotarg.add(ra.c)
                visibleNodes.add(ra.c)
    return (andornot, andornotarg)

def genNot(g: Graph, nodeLabels : dict[Node, DotNode], visibleNodes: set[Node]):
    q = f"""
         SELECT DISTINCT ?cc ?c
         WHERE {{ ?cc owl:complementOf ?c
               }}
        """
    qres = g.query(q)
    for r in qres:
        nodeLabels[r.cc] = DotNode(classname='NOT', isAndOrNot=True)
        visibleNodes.add(r.cc)
        visibleNodes.add(r.c)
        print(f"""   "{r.cc}" [label="NOT", shape="rectangle", color="green"] ;""")
        print(f"""   "{r.cc}" -> "{r.c}" [color="black"] ;""")


def genSub(g: Graph, restrOnDtype: set[Node], visibleNodes: set[Node]):
    """
    Show subclass as edges
    """
    print("""
    
    /// Subclasses
    
    """)
    showSubclasses = False

    subc = set()
    
    qref =  f"""
                SELECT DISTINCT ?x ?y 
                WHERE {{ ?x rdfs:subClassOf ?y 
                }}
                """
    qrefres = g.query(qref)

    for r in qrefres:
        if r.y not in restrOnDtype:
            print(f'  "{r.x}" -> "{r.y}" [ arrowhead="onormal", color="{SUBCLASS_LINK_COLOR}"]; ')
            subc.add(r.x)
            subc.add(r.y)
            visibleNodes.add(r.x)
            visibleNodes.add(r.y)
    return subc


def genEquiv(g: Graph, visibleNodes: set[Node]):
    # Equivalent Classes

    eqc = set()
    qref =  f"""
                SELECT DISTINCT ?x ?y 
                WHERE {{ ?x owl:equivalentClass ?y 
                }}
                """
    qrefres = g.query(qref)

    for r in qrefres:
            print(f'  "{r.x}" -> "{r.y}" [ dir="both", color="black:black", arrowhead="onormal", arrowtail="onormal"]; ')
            eqc.add(r.x)
            eqc.add(r.y)
            visibleNodes.add(r.x)
            visibleNodes.add(r.y)
    return eqc

def addUpperLevel(g: Graph, subOfRestr: set[tuple[Node,Node]], visibleNodes: set[Node]):
    """
    Show the superclasses of all the visible classes
    """
    newVisible = set()
    newSubEdge = set()
    print("// Upper level Subc")
    for v in visibleNodes:
        qup = f"""
                SELECT DISTINCT ?x ?y
                WHERE {{ <{v}> rdfs:subClassOf* ?x. ?x rdfs:subClassOf ?y
                    FILTER NOT EXISTS{{?y rdf:type owl:Restriction }}
                }}
              """
        qres = g.query(qup)
        for r in qres:
            ##print(f"// {r.x} {r.y}")
            if  (r.x, r.y) not in newSubEdge and (r.x, r.y) not in subOfRestr : # and r.x not in visibleNodes and r.y not in visibleNodes  :
                print(f'  "{r.x}" -> "{r.y}" [ arrowhead="onormal", color="orange"]; ')
                newSubEdge.add((r.x, r.y))
                newVisible.add(r.x)
                newVisible.add(r.y)
    visibleNodes.update(newVisible)
    print("// End upper level")

def genAnnotations(g: Graph, nodeLabels : dict[Node, DotNode], visibleNodes: set[Node]):
    print('''
    
    // Annotations
    
    ''')
    qa =  f"""
                SELECT DISTINCT ?x ?a (GROUP_CONCAT(STR(?y) ; separator="\\\\l - ") AS ?vals) 
                WHERE {{ ?a a owl:AnnotationProperty .
                         ?x ?a ?y 
                }}
                GROUP BY ?x ?a
                """
    qres = g.query(qa)

    withLabels = set()
    for r in qres:
        targetid = str(r.x) + '-' + str(r.a)
        property = makelabel(g, r.a)
        if r.x not in nodeLabels:
            nodeLabels[r.x] = DotNode(classname=makelabel(g, r.x))
        value = r.vals
        if 'label' in property.lower() or 'term' in property.lower():
            nodeLabels[r.x].annotations += property + ":\\l\ - <B>" + r.vals + "</B>\\l"
        else:
            print(f'  "{r.x}" -> "{targetid}" [ label="{property}" color="orange"]; ')
            visibleNodes.add(targetid)
            nodeLabels[targetid] = DotNode(classname=r.vals, isAnnotVal=True)



print('digraph {')
print('  rankdir="BT"')

dotnodelabel: dict[Node, DotNode] = {}   ## node IRI to dot node name
visibleNodes = set()

(objRest, objRestrArg, subToRestr) = genObjRestr(g, dotnodelabel, visibleNodes)
subRestr = {x for pair in subToRestr for x in pair}

dtypeRest = genDatatypeRestr(g, dotnodelabel, visibleNodes)

genDomRng(g, dotnodelabel, visibleNodes)

(andOrNot, andOrNotArg) = genAndOr(g, dotnodelabel, visibleNodes, subToRestr)

genNot(g, dotnodelabel, visibleNodes)

subc = genSub(g, dtypeRest, visibleNodes)

eqc = genEquiv(g, visibleNodes)

if annot_flag : 
    genAnnotations(g, dotnodelabel, visibleNodes)

### addUpperLevel(g, subToRestr, visibleNodes)

#for x in eqc.union(subc.union(andOrNotArg.union(objRestrArg.union(subRestr)))):
for x in visibleNodes:
    if x not in dotnodelabel : dotnodelabel[x] = DotNode(classname=makelabel(g, x))

##### Add the labels

print("""

// Labels

""")
for nid in visibleNodes: # dotnodelabel:
    n = dotnodelabel[nid]
    if  n.isPropRestr:
        print(f"""   "{nid}" [shape="rectangle", height="0", label=" "] ;""")
    elif n.isAnnotVal:
        print(f"""   "{nid}" [shape="rectangle", color="green", label="{n.classname}"] ;""")
    elif n.isAndOrNot:
        pass
    else:
        if n.classname == '*':
            cls_display = '<i>Thing</i>'
        else: 
            cls_display = f'<b>{n.classname}</b>'
        lab = f"""<table BORDER="0" CELLBORDER="1" CELLSPACING="0" ><tr><td>{cls_display}</td></tr>"""
        if n.annotations != '':
            lab += f"""<tr><td align="left">{n.annotations}</td></tr>"""
        if n.attributes != '':
            lab += f"""<tr><td align="left">{n.attributes}</td></tr>"""
        lab = lab.replace('\l','<BR ALIGN="LEFT"/>')
        lab = lab.replace('\\','')
        lab += "</table>"
        print(f"""   "{nid}" [shape="none", margin="0.05,0.02", label=<{lab}>] ;""")


print('}')
