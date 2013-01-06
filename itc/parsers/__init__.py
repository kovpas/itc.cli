import html5lib

htmlParser = html5lib.HTMLParser(tree=html5lib.treebuilders.getTreeBuilder("lxml")
                                 , namespaceHTMLElements=False)
