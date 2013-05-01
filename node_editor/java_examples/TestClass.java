class TestClass extends SomeOtherClass<Object> {

    private static char unimap[] = {
        12,
        13,
        14
    };

    public static void main(){
        int x = 12;   // Integer
        int x = 0x12; // Integer in HexForm
    }

    private void _Bla(){
        System.out.println("Unknown ESC [...  \"" + c);
        String escape = "\b";
    }

    private void _SetCursor(int row, int col) {
        int maxr = getRows();
      int tm = getTopMargin();

      R = (row < 0)?0:row;
      C = (col < 0)?0:col;

      if (!moveoutsidemargins) {
        R += tm;
        maxr = getBottomMargin();
      }
      if (R > maxr) R = maxr;
    }

}
