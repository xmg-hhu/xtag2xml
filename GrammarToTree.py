import re
import os
import utils
import pprint
import simplejson as json


class grammarTree:
    def __init__(self, definition, sourcefilename):
        self.family = sourcefilename.split(".",1)[0]
        self.family = re.sub("\x03", "beta", re.sub("\x02", "alpha", self.family))
        self.name = definition.split('"',2)[1]
        self.name = re.sub("\x03", "beta", re.sub("\x02", "alpha", self.name))
        self.nodes = self.getNodes(definition)
        self.hierarchy = self.getHierarchy(definition)

    def getNodes(self, definition):
        # find the "S_r.b" part in line "S_r.b:<inv> = -":
        node = re.compile("([A-Za-z_0-9]+(_r)?)\.((b|t))")
        nodes = {}
        for result in re.findall(node, definition):
            nodeName = result[0]
            topOrBottom = result[2]
            if nodeName in nodes:
                if not topOrBottom in nodes[nodeName]:
                    nodes[nodeName].update({topOrBottom: {}})
            else:
                nodes[nodeName] = {topOrBottom: {}}

        # differentiate between absolute feature values and values that
        # reference other nodes
        absoluteValue = re.compile("([A-Za-z_0-9]+(_r)?)\.(b|t):(<[a-z-]+>)\s*=\s*([^:\s]+)\s")
        relativeValue = re.compile("([A-Za-z_0-9]+(_r)?)\.(b|t):(<[a-z-]+>)\s*=\s*([A-Za-z_0-9]+(_r)?)\.(b|t):(<[a-z-]+>)")
        for result in re.findall(absoluteValue, definition):
            nodeName = result[0]
            topOrBottom = result[2]
            feature = result[3]
            featureValue = result[4]
            if '"' in featureValue:
                featureValue = featureValue.rsplit('"')[0]
            if not feature in nodes[nodeName][topOrBottom]:
                nodes[nodeName][topOrBottom][feature] = featureValue

        # map variable names like "@A" to dictionaries of nodes like "{node: {top: feature}}"
        self.variables = {}
        for result in re.findall(relativeValue, definition):
            nodeName = result[0]
            topOrBottom = result[2]
            feature = result[3]
            relatedNodeName = result[4]
            relatedNodeTopOrBottom = result[6]
            relatedNodeFeature = result[7]
            # find out if referenced node has an absolute value! if it does,
            # copy the value to this node.
            if relatedNodeFeature in nodes[relatedNodeName][relatedNodeTopOrBottom]:
                nodes[nodeName][topOrBottom][feature] = nodes[relatedNodeName][relatedNodeTopOrBottom][relatedNodeFeature]
            else:
                node1 = {nodeName: {topOrBottom: feature}}
                node2 = {relatedNodeName: {relatedNodeTopOrBottom: relatedNodeFeature}}
                found = False
                for reference in self.variables:
                    newDict1 = self.variables[reference].copy()
                    newDict2 = self.variables[reference].copy()
                    newDict1.update(node1)
                    newDict2.update(node2)
                    if self.variables[reference] == newDict1:
                        if not self.variables[reference] == newDict2:
                            self.variables[reference].update(node2)
                            found = True
                    elif self.variables[reference] == newDict2:
                        if not self.variables[reference] == newDict1:
                            self.variables[reference].update(node1)
                            found = True
                if not found:
                    addition = node1.copy()
                    addition.update(node2)
                    self.variables["@"+utils.numberToString(len(self.variables))] = addition

        nodes = utils.mergeDicts(nodes, self.variables)
        return(nodes)

    def getHierarchy(self, definition):
        # identify the part of the .trees file where the tree structure is explicitly encoded
        structure_notation = re.compile("\s(?=\(+\")")
        self.hierarchy = re.split(structure_notation, definition, 1)[-1]
        self.hierarchy = re.sub("\x06", "epsilon", self.hierarchy)
        self.hierarchy = utils.bracketToDict(self.hierarchy, self.nodes)
        return self.hierarchy

def getTrees(family, xtag_dir):
    """
    string, string -> list of grammarTrees
    For the given file in the XTAG path, collect all tree definitions
    and return a list of the corresponding grammarTree objects
    """
    infile = open(xtag_dir+"/"+family, "r", encoding="utf8")
    doc = infile.read()
    trees = []

    # identify all trees in this document
    treeDefinition = re.compile("(^|\s)(?=\(\")")
    doc = re.split(treeDefinition,doc)
    for treeDef in doc:
        treeDef = treeDef.strip()
        if treeDef:
            try:
                newTree = grammarTree(treeDef, family)
                trees.append(newTree)
            except TypeError as e:
                print(e, family)
    return trees

def convertXTAGtoJSON(xtag_dir, json_dir):
    """
    string, string -> None
    Main entry point for this module. Processes all *.trees files in the XTAG
    directory and generates the corresponding JSON files in the JSON directory.
    """
    xtag_dir = xtag_dir.strip("/")
    json_dir = json_dir.strip("/")
    pp = pprint.PrettyPrinter(depth=3)
    for family in os.listdir(xtag_dir):
        try:
            os.makedirs(json_dir + "/"+family.split(".",1)[0])
        except FileExistsError:
            pass
            #print("Directory "+family.split(".",1)[0]+" already exists")
        for tree in getTrees(family, xtag_dir):
            allInfos = {}
            allInfos.update({"FAMILY": tree.family, "NAME": tree.name, "HIERARCHY": tree.hierarchy})
            with open(json_dir+"/"+tree.family+"/"+tree.name+".json", "w", encoding="utf8") as outfile:
                json.dump(allInfos, outfile, indent=4)