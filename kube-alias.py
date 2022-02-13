#!/usr/bin/env python3
import os
import subprocess
import re
import sys

CGREEN = '\33[32m'
CEND = '\033[0m'

dollaRE = re.compile("\$[0-9]+$")       # noqa: W605

_CMD_MAP = {
    "key": "kubectl",
    "description": "Kubernetes CLI",
    "children": [
        {
            "key": "get",
            "description": "Get Kubectl objects",
            "children": [
                {
                    "key": "pods",
                    "description": "List pods",
                    "terminal": True,
                    "match-args": "-A",
                },
                {
                    "key": "namespaces",
                    "description": "List namespaces",
                    "terminal": True,
                }
            ]
        },
        {
            "key": "describe",
            "description": "Describe Kubectl objects",
            "children": [
                {
                    "key": "pod",
                    "description": "Describe pods",
                    "terminal": True,
                    "match-cmds": [
                        {
                            "cmd": "kubectl get pods -A",
                            "extract": ["$1", "-n", "$0"],
                            "max-matches": 1
                        }
                    ],
                    "match-append": True
                },
                {
                    "key": "pv",
                    "description": "Describe pv",
                    "terminal": True,
                    "match-cmds": [
                        {
                            "cmd": "kubectl get pv -A",
                            "extract": ["$0"],
                            "max-matches": 1
                        }
                    ],
                    "match-append": True
                },
                {
                    "key": "pvc",
                    "description": "Describe pvc",
                    "terminal": True,
                    "match-cmds": [
                        {
                            "cmd": "kubectl get pvc -A",
                            "extract": ["$1", "-n", "$0"],
                            "max-matches": 1
                        }
                    ],
                    "match-append": True
                }
            ]
        },
        {
            "key": "edit",
            "description": "Edit Kubectl objects",
            "children": [
                {
                    "key": "cm",
                    "description": "Edit configmap",
                    "terminal": True,
                    "match-cmds": [
                        {
                            "cmd": "kubectl get cm -A",
                            "extract": ["$1", "-n", "$0"],
                            "max-matches": 1
                        }
                    ],
                    "match-append": True
                },
                {
                    "key": "deployment",
                    "description": "Edit deployment",
                    "terminal": True,
                    "match-cmds": [
                        {
                            "cmd": "kubectl get deployments -A",
                            "extract": ["$1", "-n", "$0"],
                            "max-matches": 1
                        }
                    ],
                    "match-append": True
                }
            ]
        },
        {
            "key": "exec",
            "description": "Execute a command",
            "terminal": True,
            "match-cmds": [
                {
                    "cmd": "kubectl get pods -A",
                    "extract": ["-it", "$1", "-n", "$0"],
                    "max-matches": 1
                }
            ],
            "default-args": ["-- bash"],
            "match-append": True
        },
        {
            "key": "delete",
            "description": "Delete Kubectl objects",
            "children": [
                {
                    "key": "pod",
                    "description": "Delete pod",
                    "terminal": True,
                    "match-cmds": [
                        {
                            "cmd": "kubectl get pods -A",
                            "extract": ["$1", "-n", "$0"],
                            "max-matches": 1
                        }
                    ],
                    "match-append": True
                }
            ]
        },
        {
            "key": "logs",
            "description": "Displaylogs",
            "terminal": True,
            "match-cmds": [
                {
                    "cmd": "kubectl get pods -A",
                    "extract": ["$1", "-n", "$0"],
                    "max-matches": 1
                }
            ],
            "match-append": True
        }
    ]
}


def run_cmd(cmd, sudo=False, ignore_error=False, log=False, remote_host=None, exit_on_failure=True, decodeOut=True):
    if sudo:
        cmd = "sudo {}".format(cmd)
    if remote_host and remote_host not in ['127.0.0.1', 'localhost']:
        cmd = "ssh {} -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \"{}\"".format(remote_host, cmd)
    if log:
        print("Running command: \"{}\"".format(cmd))

    p = subprocess.Popen([cmd], shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ.copy(), executable="/bin/bash")
    out, err = p.communicate()
    if log:
        try:
            print("command {} produced: {}, retcode {}, ERR: {}".format(cmd, out.strip().decode("utf-8"), p.returncode, err.strip().decode('utf-8')))
        except Exception:
            print(cmd)
            print(out.strip().decode("utf-8"))
            print(p.returncode)
            print(err.strip().decode('utf-8'))

    if decodeOut:
        out = out.strip().decode("utf-8")

    err = err.strip().decode('utf-8')
    if exit_on_failure:
        if p.returncode:
            msg = "Error running cmd: \"{}\", out \"{}\", err \"{}\", retCode {}".format(cmd, out, err, p.returncode)
            raise Exception(msg)
    return out, err, p.returncode


usageStr = """

kube-alias is a utility to work across namespaces with ease. Assumiing you have this alias setup: "alias k='python /home/utils/bin/kubeCmd.py'"

Usage Examples:
    k g p               : Will do 'kubectl get pods' (only default namespace)
    k g p <matchStr>    : will match any pod (across namespaces) with name <matchStr>
    k d pvc <matchStr>  : will run 'kubectl describe pvc <pod matching matchStr>'
    k d pv <matchStr>   : will run 'kubectl describe pv <pod matching matchStr>'
    k d p <matchStr>    : will run 'kubectl describe pod <pod matching matchStr>'
    k e <matchStr>      : will run 'kubectl exec -it <pod matching matchStr> sh'
      - k e minio (will effectively run: kubectl -n minio-ns exec -it minio-7d9889c68d-xgzzt sh)
    k l <matchStr>      : will run 'kubectl logs pod <pod matching matchStr> -n <auto-determine-namespace>'
      - k l api (will effectively run: kubectl -n mgmt-ns logs flask-api-6954587df6-cdv6s)

Note: if you see commands taking time, its kubectl taking time (and not this utility :-)

"""


def execute_commands(cmds=[], printCmd=True):
    try:
        for cmd in cmds:
            if printCmd:
                print("\nExecuting : " + CGREEN + cmd + CEND)
                print("-" * (len(cmd) + 12) + "\n")
            os.system(cmd)
    except Exception as e:
        msg = "execute_commands:: Error - {}".format(str(e))
        print(msg)
        sys.exit(1)


def gatherNodeCommands(node=None, path=[], commands=[]):
    terminal = node.get("terminal", False)
    children = node.get("children", [])
    if not path:
        path.append(node["key"])
    if not children or terminal:
        commands.append(" ".join(path))
    for child in children:
        path.append(child["key"])
        gatherNodeCommands(node=child, path=path, commands=commands)
        path.pop()


def printHelp():
    node = _CMD_MAP
    commands = []
    gatherNodeCommands(node=node, path=[], commands=commands)
    print(usageStr)
    print("List of supported commands:")
    for command in commands:
        print("   {}".format(command))


def printInvalidToken(token, cmdList):
    cmd = " ".join(cmdList)
    err = "\nInvald token: \"{} ".format(cmd)
    errLen = len(err)
    err += "{}\"".format(token)
    pointerStr = "-" * (errLen - 1) + "^"
    print(err)
    print("{}\n".format(pointerStr))
    exit(2)


def getMatchingChildren(children, token, cmdList=[]):
    tokenLen = len(token)
    matches = []
    exactMatches = []
    matchedKeys = []
    for idx, child in enumerate(children):
        key = child["key"]
        keyLen = len(key)
        if tokenLen > keyLen:
            continue
        if token == key[:tokenLen]:
            matches.append(idx)
            matchedKeys.append(key)
            if len(token) == len(key):
                exactMatches.append(idx)
    numMatches = len(matches)
    if numMatches == 1:
        # we can proceed
        return matches[-1]
    elif numMatches > 1:
        if exactMatches and len(exactMatches) == 1:
            return exactMatches[0]
        print("'{}' matches multiple possible options".format(token))
        for key in matchedKeys:
            print("    {}".format(key))
        print("Please provide more specific input")
        sys.exit(3)
    return None


def parseTokens(node=None, tokens=[], cmdList=[]):
    if not all([node, tokens]):
        raise Exception("Missing node/tokens")
    key = node["key"]
    tNode = {}
    cmd = ""
    for tIdx, token in enumerate(tokens):
        if len(token) > len(key):
            if tNode:
                break
            printInvalidToken(token, cmdList)

        # Find matching child node for the token
        children = node.get("children", [])
        if children:
            matchingIdx = getMatchingChildren(children, token, cmdList=cmdList)
            if matchingIdx is None:
                if not tNode:
                    printInvalidToken(token, cmdList=cmdList)
                break

            child = children[matchingIdx]
            node = child

            key = node["key"]
            cmdList.append(key)
            terminal = node.get("terminal", False)
            if terminal:
                # there could be commands that have more matching nodes even though we hit a terminal node.. e.g
                # cmd1: <some-cmd> <get> <args>
                # cmd2: <some-cmd> <get> <args> <detailed>
                # <get> would be a terminal node but it is possible to have another terminal node if we find <detailed>
                tNode["cmd"] = " ".join(cmdList)
                tNode["match-args"] = node.get("match-args")
                tNode["default-args"] = node.get("default-args")
                tNode["match-cmds"] = node.get("match-cmds", [])
                tNode["match-append"] = node.get("match-append", False)
                tNode["args"] = tokens[tIdx + 1:]

    if not tNode:
        import pdb
        pdb.set_trace()
        # print("Final node {}".format(node))
        cmd = " ".join(cmdList)
        terminal = node.get("terminal", False)
        if not terminal:
            print("Incomplete command \"{}\"".format(cmd))
            sys.exit(4)
        tNode["cmd"] = " ".join(cmdList)
        tNode["match-args"] = node.get("match-args")
        tNode["default-args"] = node.get("default-args")
        tNode["match-cmds"] = node.get("match-cmds", [])
        tNode["match-append"] = node.get("match-append", False)
        tNode["args"] = tokens[tIdx + 1:]

    # We have a terminal node.
    # If there are match-args, then add that to the command to get final command
    # Run the final command and match every output line with args
    finalCmd = tNode["cmd"]
    matchArgs = tNode["args"]
    matchCmds = tNode["match-cmds"]
    matchAppend = tNode["match-append"]
    finalArgs = []
    if not matchCmds:
        finalArgs = matchArgs
    else:
        for matchCmd in matchCmds:
            # we have a match cmd
            matchSplit = matchCmd.get("split")
            matchExtract = matchCmd.get("extract")
            maxMatches = matchCmd.get("max-matches")
            cmd = "{}".format(matchCmd["cmd"])
            matchFilterArgs = [x for x in matchArgs if "-" != x[0]]
            matchFilterExcludedArgs = [x for x in matchArgs if "-" == x[0]]
            if matchFilterArgs:
                cmd += " | egrep \"{}\"".format("|".join(matchFilterArgs))
            out, err, retCode = run_cmd(cmd)
            if retCode:
                print("Error running \"{}\", out {} err {} retCode {}".format(cmd, out, err, retCode))
                sys.exit(5)
            lines = out.split("\n")
            for line in lines:
                line = line.strip()
                if matchExtract:
                    res = []
                    if matchSplit:
                        sp = line.split(matchSplit)
                    else:
                        sp = line.split()
                    for token in matchExtract:
                        if dollaRE.match(token):
                            replacedToken = token.replace("$", "")
                            try:
                                tokenIdx = int(replacedToken)
                            except Exception:
                                print(f"Unable to parse dollar value {token}")
                                sys.exit(7)
                            if tokenIdx >= len(sp):
                                print("Invalid  field index {} for line '{}'. ".format(tokenIdx, line))
                                sys.exit(7)
                            res.append(sp[tokenIdx])
                        else:
                            res.append(token)
                    res += matchFilterExcludedArgs
                    line = " ".join(res)
                finalArgs.append(line)
            if maxMatches is not None:
                if len(finalArgs) != maxMatches:
                    print("command '{}' has multiple matches: ".format(cmd))
                    for fa in finalArgs:
                        print("    {}".format(fa))
                    print("{} needs {} match. Provide more specific substring input".format(finalCmd, maxMatches))
                    sys.exit(6)
            print(finalArgs)

    matchArgs = tNode["match-args"]
    defaultArgs = tNode["default-args"]
    if matchArgs:
        finalCmd += " {}".format(matchArgs)
    if finalArgs:
        if matchAppend:
            finalCmd += " {}".format(" ".join(finalArgs))
        else:
            finalCmd += " | egrep \"{}\"".format("|".join(finalArgs))
    if not matchArgs and defaultArgs:
        finalCmd += " {}".format(" ".join(defaultArgs))
    return finalCmd


def main():
    if len(sys.argv) < 2:
        print("Usage: {} <arguments>".format(sys.argv[0]))
        sys.exit(1)

    if sys.argv[1][0:2].lower() == "-h":
        printHelp()
        sys.exit(0)

    node = _CMD_MAP
    cmdList = [node["key"]]
    # import pdb; pdb.set_trace()
    # tokens = [node["key"][0]]
    tokens = sys.argv[1:]
    cmd = parseTokens(node=node, tokens=tokens, cmdList=cmdList)
    print(cmd)
    execute_commands([cmd])


if __name__ == "__main__":
    main()
