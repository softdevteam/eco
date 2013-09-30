class Test(object):
    def __init__(self, elements):
        self.elements = elements

    def __getitem__(self, index):
        return self.elements[index]
