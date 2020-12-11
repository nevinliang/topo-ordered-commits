'''
Author:         Nevin Liang
Date:           12.6.20
Program:        topo_order_commits.py
Description:    runs topological sort on commits in a git repository
'''

'''
Notes on strace: strace outputted nothing when called in linuxsrv09
Invoked: strace python3 topo_order_commits.py 2>strace_log
'''

########## BEGIN CODE ##########

import os
import sys
import zlib

'''
CommitNode object:
    contains commit_hash, parents, children, branches
        parents/children are sets (unique values)
        branches is a list
        commit_hash is a string
'''
class CommitNode:
    def __init__(self, commit_hash, branches=[]):
        self.commit_hash = commit_hash
        self.parents = set()
        self.children = set()
        self.branches = branches

'''
git_check helper: loops up directories until it finds .git

NOTE: returns true if it finds .git as a file (the function that
    called it will check if it is a directory or not)
'''
def git_exists():
    # takes advantage of os libraries listdir and chdir and getcwd
    while os.getcwd() != '/' and '.git' not in os.listdir():
        os.chdir('../')
    return '.git' in os.listdir()

'''
git_check: exits if git folder does not exist
'''
def git_check():
    # checks if .git dir/file exists
    if not git_exists():
        sys.stderr.write('Not inside a Git repository\n')
        exit(1)
    gitfold = os.path.join(os.getcwd(), '.git')
    # now checks to make sure .git is a directory
    if not os.path.isdir(gitfold):
        sys.stderr.write('Not inside a Git repository\n')
        exit(1)
    # go to the git folder
    os.chdir(gitfold)

'''
make_branchmap: returns a dictionary {hash code: [branch names]}
'''
def make_branchmap():
    # initialize dict to return
    branch_map = {}
    # go to heads folder
    os.chdir('./refs/heads')
    # walk through all directories
    for root, dirs, files in os.walk("."):
        for name in files + dirs:
            if os.path.isfile(os.path.join(root, name)):
                branch_name = os.path.join(root, name)[2:]
                fopen = open(branch_name, 'r')
                hash = fopen.read()[:-1]
                # if not exist already add it to the dict
                if hash not in branch_map.keys():
                    branch_map[hash] = [branch_name]
                else:
                    branch_map[hash].append(branch_name)
                fopen.close()
    # go back to the .git directory
    os.chdir('../../')
    return branch_map

'''
parent_hash: gets the parent hash codes from a detail string
'''
def parent_hash(dets):
    # just uses string manipulation to get the parent hash code
    # from the big paragraph detail string inside the objs directory
    parents = []
    for line in dets.split('\n'):
        if line.startswith('parent'):
            parents.append(line.split(' ')[1])
    return parents

'''
get_parents: get list of parents of a certain commit hash
'''
def get_parents(hash):
    # assume already in objs directory
    h1, h2 = hash[0:2], hash[2:]
    # get the detail string
    os.chdir(os.path.join('.', h1))
    c_f = open(h2, 'rb')
    # decompress to get the detail string
    dets = zlib.decompress(c_f.read()).decode()
    c_f.close()
    os.chdir('../')
    # pass it to parent_hash helper function
    return parent_hash(dets)

'''
make_DAG: recurses to create directional acyclic graph
    returns a list of root_commit hashes as well as node_map
    node_map is the BIG dict that maps hashes to nodes
'''
def make_DAG(branch_map):
    # have to go into ./objects to use get_parents
    os.chdir('./objects')
    # perform recursion for every hash in branch_map
    # which contains the hashes/names for every leaf_commit
    node_map = {}
    root_commits = set()
    # loop through all
    for hash in branch_map:
        # if in the keys aka a leaf commit
        if hash in node_map.keys():
            # dont need to make another commitnode
            node_map[hash].branches = branch_map[hash]
        else:
            # if it doesnt exist make a new commit node, recurse
            node_map[hash] = CommitNode(hash, branch_map[hash])
            stack = [node_map[hash]]
            while len(stack) != 0:
                node = stack.pop()
                parent_hashes = get_parents(node.commit_hash)
                # go through all parents
                if len(parent_hashes) == 0:
                    root_commits.add(node.commit_hash)
                for p in parent_hashes:
                    # creates another commitnode object if it doesnt exist
                    if p not in node_map.keys():
                        node_map[p] = CommitNode(p)
                    # make connections of parents/children
                    node.parents.add(node_map[p])
                    node_map[p].children.add(node)
                    stack.append(node_map[p])
    os.chdir('../')
    # returns a list of root_commit hashes as well as node_map
    # node_map is the BIG dict that maps hashes to nodes
    return list(root_commits), node_map


'''
topo_sort: topologically sorts the commits and returns as list
'''
def topo_sort(root_commits, node_map):
    # L is output resulting list
    # vis is visted. used set because uniqueness and easy to lookup
    # stack: recursion stack (functional recursion is too slow/too deep)
    L, vis, stack = [], set(), root_commits.copy()
    # recursion loop
    while len(stack) != 0:
        top = stack[-1]
        vis.add(top)
        children = [c for c in node_map[top].children if c.commit_hash not in vis]
        # stop recursing if no more children
        if len(children) == 0:
            stack.pop()
            # add to output list
            L.append(top)
        else:
            stack.append(children[0].commit_hash)
    return L

'''
output: prints out topolist in the form that the specs want
'''
def output(topo_list, node_map):
    # loop through every element in topo list
    for i in range(len(topo_list)):
        # current node
        n1 = node_map[topo_list[i]]

        # print "hash branch-name"
        if len(n1.branches) == 0:
            print(topo_list[i])
        else:
            print(topo_list[i] + " ", end="")
            print(*sorted(n1.branches))

        # if next is not parent print sticky
        if i < (len(topo_list) - 1):
            # next node
            n2 = node_map[topo_list[i + 1]]
            if topo_list[i + 1] not in [p.commit_hash for p in n1.parents]:
                # print parent then children
                print(*[p.commit_hash for p in n1.parents], end="=\n\n=")
                print(*[c.commit_hash for c in n2.children])

'''
topo_order_commits: essentially the driving function
'''
def topo_order_commits():
    # first check if git exists (exit if not)
    git_check()
    # create leafnode/branches
    branch_map = make_branchmap()
    # make DAG and create node map and root_commit list
    root_commits, node_map = make_DAG(branch_map)
    # topo sort
    topo_list = topo_sort(root_commits, node_map)
    # and output
    output(topo_list, node_map)

if __name__ == '__main__':
    topo_order_commits()

########## END CODE ##########
