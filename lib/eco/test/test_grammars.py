from grammars.grammars import java
from treemanager import TreeManager

class Test_Java:
    def setup_class(cls):
        parser, lexer = java.load()
        cls.lexer = lexer
        cls.parser = parser
        cls.parser.init_ast()
        cls.ast = cls.parser.previous_version
        cls.treemanager = TreeManager()
        cls.treemanager.add_parser(cls.parser, cls.lexer, java.name)

    def reset(self):
        self.parser.reset()
        self.treemanager = TreeManager()
        self.treemanager.add_parser(self.parser, self.lexer, java.name)

    def test_floats_ints(self):
        self.reset()
        program = """class C {
    float a = 1F;
    int b = 0_123;
    int c = 0b110;
    long d = 0b110L;
    float f = 0.e1F;
    float g = 0F;
    float h = 0e1F;
    int i = 0e1;
    public main(){
        r.d();
    }
}"""
        self.treemanager.import_file(program)
        assert self.parser.last_status == True
