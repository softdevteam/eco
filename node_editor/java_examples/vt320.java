package de.mud.terminal;

import java.util.Properties;
import java.awt.event.KeyEvent;

public abstract class vt320 extends VDUBuffer implements VDUInput {
  public final static String ID = "$Id: vt320.java 507 2005-10-25 10:14:52Z marcus $";

  private final static int debug = 0;

  public abstract void write(byte[] b);

  public void beep() {
  }

  public void putString(String s) {
    int len = s.length();

    if (len > 0) {
      markLine(R, 1);
      for (int i = 0; i < len; i++) {
        putChar(s.charAt(i), false);
      }
      setCursorPosition(C, R);
      redraw();
    }
  }

  protected void sendTelnetCommand(byte cmd) {
  }

  protected void setWindowSize(int c, int r) {
  }

  public void setScreenSize(int c, int r, boolean broadcast) {
    int oldrows = getRows(), oldcols = getColumns();

    if (debug>2) System.err.println("setscreensize ("+c+","+r+","+broadcast+")");

    super.setScreenSize(c,r,false);

    if (r > oldrows) {
      setCursorPosition(C, R + (r-oldrows)); 
      redraw();
    }
    if (broadcast) {
      setWindowSize(c, r);
    }
  }


  public vt320(int width, int height) {
    super(width, height);
    setVMS(false);
    setIBMCharset(false);
    setTerminalID("vt320");
    setBufferSize(100);

    int nw = getColumns();
    if (nw < 132) nw = 132;
    Tabs = new byte[nw];
    for (int i = 0; i < nw; i += 8) {
      Tabs[i] = 1;
    }

    PF1 = "001bOP";
    PF2 = "001bOQ";
    PF3 = "001bOR";
    PF4 = "001bOS";

    Insert = new String[4];
    Remove = new String[4];
    KeyHome = new String[4];
    KeyEnd = new String[4];
    NextScn = new String[4];
    PrevScn = new String[4];
    Escape = new String[4];
    BackSpace = new String[4];
    TabKey = new String[4];
    Insert[0] = Insert[1] = Insert[2] = Insert[3] = "001b[2~";
    Remove[0] = Remove[1] = Remove[2] = Remove[3] = "001b[3~";
    PrevScn[0] = PrevScn[1] = PrevScn[2] = PrevScn[3] = "001b[5~";
    NextScn[0] = NextScn[1] = NextScn[2] = NextScn[3] = "001b[6~";
    KeyHome[0] = KeyHome[1] = KeyHome[2] = KeyHome[3] = "001b[H";
    KeyEnd[0] = KeyEnd[1] = KeyEnd[2] = KeyEnd[3] = "001b[F";
    Escape[0] = Escape[1] = Escape[2] = Escape[3] = "001b";
    if (vms) {
      BackSpace[1] = "" + (char) 10;
      BackSpace[2] = "0018";
      BackSpace[0] = BackSpace[3] = "007f";
    } else {
      BackSpace[0] = BackSpace[1] = BackSpace[2] = BackSpace[3] = "\b";
    }

    Find = "001b[1~";
    Select = "001b[4~";
    Help = "001b[28~";
    Do = "001b[29~";

    FunctionKey = new String[21];
    FunctionKey[0] = "";
    FunctionKey[1] = PF1;
    FunctionKey[2] = PF2;
    FunctionKey[3] = PF3;
    FunctionKey[4] = PF4;
    FunctionKey[5] = "001b[15~";
    FunctionKey[6] = "001b[17~";
    FunctionKey[7] = "001b[18~";
    FunctionKey[8] = "001b[19~";
    FunctionKey[9] = "001b[20~";
    FunctionKey[10] = "001b[21~";
    FunctionKey[11] = "001b[23~";
    FunctionKey[12] = "001b[24~";
    FunctionKey[13] = "001b[25~";
    FunctionKey[14] = "001b[26~";
    FunctionKey[15] = Help;
    FunctionKey[16] = Do;
    FunctionKey[17] = "001b[31~";
    FunctionKey[18] = "001b[32~";
    FunctionKey[19] = "001b[33~";
    FunctionKey[20] = "001b[34~";

    FunctionKeyShift = new String[21];
    FunctionKeyAlt = new String[21];
    FunctionKeyCtrl = new String[21];

    for (int i = 0; i < 20; i++) {
      FunctionKeyShift[i] = "";
      FunctionKeyAlt[i] = "";
      FunctionKeyCtrl[i] = "";
    }
    FunctionKeyShift[15] = Find;
    FunctionKeyShift[16] = Select;


    TabKey[0] = "0009";
    TabKey[1] = "001bOP0009";
    TabKey[2] = TabKey[3] = "";

    KeyUp = new String[4];
    KeyUp[0] = "001b[A";
    KeyDown = new String[4];
    KeyDown[0] = "001b[B";
    KeyRight = new String[4];
    KeyRight[0] = "001b[C";
    KeyLeft = new String[4];
    KeyLeft[0] = "001b[D";
    Numpad = new String[10];
    Numpad[0] = "001bOp";
    Numpad[1] = "001bOq";
    Numpad[2] = "001bOr";
    Numpad[3] = "001bOs";
    Numpad[4] = "001bOt";
    Numpad[5] = "001bOu";
    Numpad[6] = "001bOv";
    Numpad[7] = "001bOw";
    Numpad[8] = "001bOx";
    Numpad[9] = "001bOy";
    KPMinus = PF4;
    KPComma = "001bOl";
    KPPeriod = "001bOn";
    KPEnter = "001bOM";

    NUMPlus = new String[4];
    NUMPlus[0] = "+";
    NUMDot = new String[4];
    NUMDot[0] = ".";
  }

  public vt320() {
    this(80, 24);
  }

  public void mousePressed(int x, int y, int modifiers) {
    if (mouserpt == 0)
      return;

    int mods = modifiers;
    mousebut = 3;
    if ((mods & 16) == 16) mousebut = 0;
    if ((mods & 8) == 8) mousebut = 1;
    if ((mods & 4) == 4) mousebut = 2;

    int mousecode;
    if (mouserpt == 9)
      mousecode = 0x20 | mousebut;
    else
      mousecode = mousebut | 0x20 | ((mods & 7) << 2);

    byte b[] = new byte[6];

    b[0] = 27;
    b[1] = (byte) '[';
    b[2] = (byte) 'M';
    b[3] = (byte) mousecode;
    b[4] = (byte) (0x20 + x + 1);
    b[5] = (byte) (0x20 + y + 1);

    write(b);
  }

  public void mouseReleased(int x, int y, int modifiers) {
    if (mouserpt == 0)
      return;


    int mousecode;
    if (mouserpt == 9)
      mousecode = 0x20 + mousebut;
    else
      mousecode = '#';

    byte b[] = new byte[6];
    b[0] = 27;
    b[1] = (byte) '[';
    b[2] = (byte) 'M';
    b[3] = (byte) mousecode;
    b[4] = (byte) (0x20 + x + 1);
    b[5] = (byte) (0x20 + y + 1);
    write(b);
    mousebut = 0;
  }


  private boolean localecho = false;

  public void setLocalEcho(boolean echo) {
    localecho = echo;
  }

  public void setVMS(boolean vms) {
    this.vms = vms;
  }

  public void setIBMCharset(boolean ibm) {
    useibmcharset = ibm;
  }

  public void setKeyCodes(Properties codes) {
    String res, prefixes[] = {"", "S", "C", "A"};
    int i;

    for (i = 0; i < 10; i++) {
      res = codes.getProperty("NUMPAD" + i);
      if (res != null) Numpad[i] = unEscape(res);
    }
    for (i = 1; i < 20; i++) {
      res = codes.getProperty("F" + i);
      if (res != null) FunctionKey[i] = unEscape(res);
      res = codes.getProperty("SF" + i);
      if (res != null) FunctionKeyShift[i] = unEscape(res);
      res = codes.getProperty("CF" + i);
      if (res != null) FunctionKeyCtrl[i] = unEscape(res);
      res = codes.getProperty("AF" + i);
      if (res != null) FunctionKeyAlt[i] = unEscape(res);
    }
    for (i = 0; i < 4; i++) {
      res = codes.getProperty(prefixes[i] + "PGUP");
      if (res != null) PrevScn[i] = unEscape(res);
      res = codes.getProperty(prefixes[i] + "PGDOWN");
      if (res != null) NextScn[i] = unEscape(res);
      res = codes.getProperty(prefixes[i] + "END");
      if (res != null) KeyEnd[i] = unEscape(res);
      res = codes.getProperty(prefixes[i] + "HOME");
      if (res != null) KeyHome[i] = unEscape(res);
      res = codes.getProperty(prefixes[i] + "INSERT");
      if (res != null) Insert[i] = unEscape(res);
      res = codes.getProperty(prefixes[i] + "REMOVE");
      if (res != null) Remove[i] = unEscape(res);
      res = codes.getProperty(prefixes[i] + "UP");
      if (res != null) KeyUp[i] = unEscape(res);
      res = codes.getProperty(prefixes[i] + "DOWN");
      if (res != null) KeyDown[i] = unEscape(res);
      res = codes.getProperty(prefixes[i] + "LEFT");
      if (res != null) KeyLeft[i] = unEscape(res);
      res = codes.getProperty(prefixes[i] + "RIGHT");
      if (res != null) KeyRight[i] = unEscape(res);
      res = codes.getProperty(prefixes[i] + "ESCAPE");
      if (res != null) Escape[i] = unEscape(res);
      res = codes.getProperty(prefixes[i] + "BACKSPACE");
      if (res != null) BackSpace[i] = unEscape(res);
      res = codes.getProperty(prefixes[i] + "TAB");
      if (res != null) TabKey[i] = unEscape(res);
      res = codes.getProperty(prefixes[i] + "NUMPLUS");
      if (res != null) NUMPlus[i] = unEscape(res);
      res = codes.getProperty(prefixes[i] + "NUMDECIMAL");
      if (res != null) NUMDot[i] = unEscape(res);
    }
  }

  public void setTerminalID(String terminalID) {
    this.terminalID = terminalID;

    if (terminalID.equals("scoansi")) {
      FunctionKey[1] = "001b[M";  FunctionKey[2] = "001b[N";
      FunctionKey[3] = "001b[O";  FunctionKey[4] = "001b[P";
      FunctionKey[5] = "001b[Q";  FunctionKey[6] = "001b[R";
      FunctionKey[7] = "001b[S";  FunctionKey[8] = "001b[T";
      FunctionKey[9] = "001b[U";  FunctionKey[10] = "001b[V";
      FunctionKey[11] = "001b[W"; FunctionKey[12] = "001b[X";
      FunctionKey[13] = "001b[Y"; FunctionKey[14] = "?";
      FunctionKey[15] = "001b[a"; FunctionKey[16] = "001b[b";
      FunctionKey[17] = "001b[c"; FunctionKey[18] = "001b[d";
      FunctionKey[19] = "001b[e"; FunctionKey[20] = "001b[f";
      PrevScn[0] = PrevScn[1] = PrevScn[2] = PrevScn[3] = "001b[I";
      NextScn[0] = NextScn[1] = NextScn[2] = NextScn[3] = "001b[G";
    }
  }

  public void setAnswerBack(String ab) {
    this.answerBack = unEscape(ab);
  }

  public String getTerminalID() {
    return terminalID;
  }

  private boolean write(String s, boolean doecho) {
    if (debug > 2) System.out.println("write(|" + s + "|," + doecho);
    if (s == null)
      return true;

    byte arr[] = new byte[s.length()];
    for (int i = 0; i < s.length(); i++) {
      arr[i] = (byte) s.charAt(i);
    }
    write(arr);

    if (doecho)
      putString(s);
    return true;
  }

  private boolean write(String s) {
    return write(s, localecho);
  }

  private String terminalID = "vt320";
  private String answerBack = "Use Terminal.answerback to set ...\n";

  int R,C;
  int attributes = 0;

  int Sc,Sr,Sa,Stm,Sbm;
  char Sgr,Sgl;
  char Sgx[];

  int insertmode = 0;
  int statusmode = 0;
  boolean vt52mode = false;
  boolean keypadmode = false;
  boolean output8bit = false;
  int normalcursor = 0;
  boolean moveoutsidemargins = true;
  boolean wraparound = true;
  boolean sendcrlf = true;
  boolean capslock = false;
  boolean numlock = false;
  int mouserpt = 0;
  byte mousebut = 0;

  boolean useibmcharset = false;

  int lastwaslf = 0;
  boolean usedcharsets = false;

  private final static char ESC = 27;
  private final static char IND = 132;
  private final static char NEL = 133;
  private final static char RI = 141;
  private final static char SS2 = 142;
  private final static char SS3 = 143;
  private final static char DCS = 144;
  private final static char HTS = 136;
  private final static char CSI = 155;
  private final static char OSC = 157;
  private final static int TSTATE_DATA = 0;
  private final static int TSTATE_ESC = 1;
  private final static int TSTATE_CSI = 2;
  private final static int TSTATE_DCS = 3;
  private final static int TSTATE_DCEQ = 4;
  private final static int TSTATE_ESCSQUARE = 5;
  private final static int TSTATE_OSC = 6;    
  private final static int TSTATE_SETG0 = 7; 
  private final static int TSTATE_SETG1 = 8;
  private final static int TSTATE_SETG2 = 9;
  private final static int TSTATE_SETG3 = 10;
  private final static int TSTATE_CSI_DOLLAR = 11; 
  private final static int TSTATE_CSI_EX = 12; 
  private final static int TSTATE_ESCSPACE = 13; 
  private final static int TSTATE_VT52X = 14;
  private final static int TSTATE_VT52Y = 15;
  private final static int TSTATE_CSI_TICKS = 16;
  private final static int TSTATE_CSI_EQUAL = 17; 

  char gx[] = {
    'B', // g0
    '0', // g1
    'B', // g2
    'B', // g3
  };
  char gl = 0;		// default GL to G0
  char gr = 2;		// default GR to G2
  int onegl = -1;	// single shift override for GL.

  // Map from scoansi linedrawing to DEC _and_ unicode (for the stuff which
  // is not in linedrawing). Got from experimenting with scoadmin.
  private final static String scoansi_acs = "Tm7k3x4u?kZl@mYjEnB2566DqCtAvM2550:2551N2557I2554;2557H255a0a<255d";
  // array to store DEC Special -> Unicode mapping
  //  Unicode   DEC  Unicode name    (DEC name)
  private static char DECSPECIAL[] = {
    'u', //5f blank
    'u', //60 black diamond
    'u', //61 grey square
    'u', //62 Horizontal tab  (ht) pict. for control
    'u', //63 Form Feed       (ff) pict. for control
    'u', //64 Carriage Return (cr) pict. for control
    'u', //65 Line Feed       (lf) pict. for control
    'u', //66 Masculine ordinal indicator
    'u', //67 Plus or minus sign
    'u', //68 New Line        (nl) pict. for control
    'u', //69 Vertical Tab    (vt) pict. for control
    'u', //6a Forms light up   and left
    'u', //6b Forms light down and left
    'u', //6c Forms light down and right
    'u', //6d Forms light up   and right
    'u', //6e Forms light vertical and horizontal
    'u', //6f Upper 1/8 block                        (Scan 1)
    'u', //70 Upper 1/2 block                        (Scan 3)
    'u', //71 Forms light horizontal or ?em dash?    (Scan 5)
    'u', //72 25ac black rect. or 2582 lower 1/4 (Scan 7)
    'u', //73 005f underscore  or 2581 lower 1/8 (Scan 9)
    'u', //74 Forms light vertical and right
    'u', //75 Forms light vertical and left
    'u', //76 Forms light up   and horizontal
    'u', //77 Forms light down and horizontal
    'u', //78 vertical bar
    'u', //79 less than or equal
    'u', //7a greater than or equal
    'u', //7b paragraph
    'u', //7c not equal
    'u', //7d Pound Sign (british)
    'u'  //7e Middle Dot
  };

  private String Numpad[];
  private String FunctionKey[];
  private String FunctionKeyShift[];
  private String FunctionKeyCtrl[];
  private String FunctionKeyAlt[];
  private String TabKey[];
  private String KeyUp[],KeyDown[],KeyLeft[],KeyRight[];
  private String KPMinus, KPComma, KPPeriod, KPEnter;
  private String PF1, PF2, PF3, PF4;
  private String Help, Do, Find, Select;

  private String KeyHome[], KeyEnd[], Insert[], Remove[], PrevScn[], NextScn[];
  private String Escape[], BackSpace[], NUMDot[], NUMPlus[];

  private String osc,dcs;

  private int term_state = TSTATE_DATA;
  private boolean vms = false;
  private byte[] Tabs;
  private int[] DCEvars = new int[30];
  private int DCEvar;

  static String unEscape(String tmp) {
    int idx = 0, oldidx = 0;
    String cmd;
    cmd = "";
    while ((idx = tmp.indexOf('u', oldidx)) >= 0 &&
            ++idx <= tmp.length()) {
      cmd += tmp.substring(oldidx, idx - 1);
      if (idx == tmp.length()) return cmd;
      switch (tmp.charAt(idx)) {
        case 'b':
          cmd += "\b";
          break;
        case 'e':
          cmd += "001b";
          break;
        case 'n':
          cmd += "\n";
          break;
        case 'r':
          cmd += "\r";
          break;
        case 't':
          cmd += "\t";
          break;
        case 'v':
          cmd += "000b";
          break;
        case 'a':
          cmd += "0012";
          break;
        default :
          if ((tmp.charAt(idx) >= '0') && (tmp.charAt(idx) <= '9')) {
            int i;
            for (i = idx; i < tmp.length(); i++)
              if ((tmp.charAt(i) < '0') || (tmp.charAt(i) > '9'))
                break;
            cmd += (char) Integer.parseInt(tmp.substring(idx, i));
            idx = i - 1;
          } else
            cmd += tmp.substring(idx, ++idx);
          break;
      }
      oldidx = ++idx;
    }
    if (oldidx <= tmp.length()) cmd += tmp.substring(oldidx);
    return cmd;
  }

  private boolean writeSpecial(String s) {
    if (s == null)
      return true;
    if (((s.length() >= 3) && (s.charAt(0) == 27) && (s.charAt(1) == 'O'))) {
      if (vt52mode) {
        if ((s.charAt(2) >= 'P') && (s.charAt(2) <= 'S')) {
          s = "001b" + s.substring(2);
        } else {
          s = "001b?" + s.substring(2);
        }
      } else {
        if (output8bit) {
          s = "008f" + s.substring(2);
        }
      }
    }
    if (((s.length() >= 3) && (s.charAt(0) == 27) && (s.charAt(1) == '['))) {
      if (output8bit) {
        s = "009b" + s.substring(2);
      }
    }
    return write(s, false);
  }

  public void keyPressed(int keyCode, char keyChar, int modifiers) {
    boolean control = (modifiers & VDUInput.KEY_CONTROL) != 0;
    boolean shift = (modifiers & VDUInput.KEY_SHIFT) != 0;
    boolean alt = (modifiers & VDUInput.KEY_ALT) != 0;

    if (debug > 1) System.out.println("keyPressed("+keyCode+", "+(int)keyChar+", "+modifiers+")");

    int xind;
    String fmap[];
    xind = 0;
    fmap = FunctionKey;
    if (shift) {
      fmap = FunctionKeyShift;
      xind = 1;
    }
    if (control) {
      fmap = FunctionKeyCtrl;
      xind = 2;
    }
    if (alt) {
      fmap = FunctionKeyAlt;
      xind = 3;
    }

    switch (keyCode) {
      case KeyEvent.VK_PAUSE:
        if (shift || control)
          sendTelnetCommand((byte) 243); // BREAK
        break;
      case KeyEvent.VK_F1:
        writeSpecial(fmap[1]);
        break;
      case KeyEvent.VK_F2:
        writeSpecial(fmap[2]);
        break;
      case KeyEvent.VK_F3:
        writeSpecial(fmap[3]);
        break;
      case KeyEvent.VK_F4:
        writeSpecial(fmap[4]);
        break;
      case KeyEvent.VK_F5:
        writeSpecial(fmap[5]);
        break;
      case KeyEvent.VK_F6:
        writeSpecial(fmap[6]);
        break;
      case KeyEvent.VK_F7:
        writeSpecial(fmap[7]);
        break;
      case KeyEvent.VK_F8:
        writeSpecial(fmap[8]);
        break;
      case KeyEvent.VK_F9:
        writeSpecial(fmap[9]);
        break;
      case KeyEvent.VK_F10:
        writeSpecial(fmap[10]);
        break;
      case KeyEvent.VK_F11:
        writeSpecial(fmap[11]);
        break;
      case KeyEvent.VK_F12:
        writeSpecial(fmap[12]);
        break;
      case KeyEvent.VK_UP:
        writeSpecial(KeyUp[xind]);
        break;
      case KeyEvent.VK_DOWN:
        writeSpecial(KeyDown[xind]);
        break;
      case KeyEvent.VK_LEFT:
        writeSpecial(KeyLeft[xind]);
        break;
      case KeyEvent.VK_RIGHT:
        writeSpecial(KeyRight[xind]);
        break;
      case KeyEvent.VK_PAGE_DOWN:
        writeSpecial(NextScn[xind]);
        break;
      case KeyEvent.VK_PAGE_UP:
        writeSpecial(PrevScn[xind]);
        break;
      case KeyEvent.VK_INSERT:
        writeSpecial(Insert[xind]);
        break;
      case KeyEvent.VK_DELETE:
        writeSpecial(Remove[xind]);
        break;
      case KeyEvent.VK_BACK_SPACE:
        writeSpecial(BackSpace[xind]);
	if (localecho) {
	  if (BackSpace[xind] == "\b") {
	    putString("\b \b"); // make the last char 'deleted'
	  } else {
	    putString(BackSpace[xind]); // echo it
	  }
	}
        break;
      case KeyEvent.VK_HOME:
        writeSpecial(KeyHome[xind]);
        break;
      case KeyEvent.VK_END:
        writeSpecial(KeyEnd[xind]);
        break;
      case KeyEvent.VK_NUM_LOCK:
        if (vms && control) {
          writeSpecial(PF1);
        }
        if (!control)
          numlock = !numlock;
        break;
      case KeyEvent.VK_CAPS_LOCK:
        capslock = !capslock;
        return;
      case KeyEvent.VK_SHIFT:
      case KeyEvent.VK_CONTROL:
      case KeyEvent.VK_ALT:
        return;
      default:
        break;
    }
  }

  public void keyReleased(KeyEvent evt) {
    if (debug > 1) System.out.println("keyReleased("+evt+")");
    // ignore
  }

  public void keyTyped(int keyCode, char keyChar, int modifiers) {
    boolean control = (modifiers & VDUInput.KEY_CONTROL) != 0;
    boolean shift = (modifiers & VDUInput.KEY_SHIFT) != 0;
    boolean alt = (modifiers & VDUInput.KEY_ALT) != 0;

    if (debug > 1) System.out.println("keyTyped("+keyCode+", "+(int)keyChar+", "+modifiers+")");

    if (keyChar == '\t') {
      if (shift) {
        write(TabKey[1], false);
      } else {
        if (control) {
          write(TabKey[2], false);
        } else {
          if (alt) {
            write(TabKey[3], false);
          } else {
            write(TabKey[0], false);
          }
        }
      }
      return;
    }
    if (alt) {
      write("" + ((char) (keyChar | 0x80)));
      return;
    }

    if (((keyCode == KeyEvent.VK_ENTER) || (keyChar == 10))
            && !control) {
      write("\r", false);
      if (localecho) putString("\r\n"); // bad hack
      return;
    }

    if ((keyCode == 10) && !control) {
      System.out.println("Sending \\r");
      write("\r", false);
      return;
    }

    if (((!vms && keyChar == '2') || keyChar == ' ') && control)
      write("" + (char) 0);

    if (vms) {
      if (keyChar == 127 && !control) {
        if (shift)
          writeSpecial(Insert[0]);        //  VMS shift delete = insert
        else
          writeSpecial(Remove[0]);        //  VMS delete = remove
        return;
      } else if (control)
        switch (keyChar) {
          case '0':
            writeSpecial(Numpad[0]);
            return;
          case '1':
            writeSpecial(Numpad[1]);
            return;
          case '2':
            writeSpecial(Numpad[2]);
            return;
          case '3':
            writeSpecial(Numpad[3]);
            return;
          case '4':
            writeSpecial(Numpad[4]);
            return;
          case '5':
            writeSpecial(Numpad[5]);
            return;
          case '6':
            writeSpecial(Numpad[6]);
            return;
          case '7':
            writeSpecial(Numpad[7]);
            return;
          case '8':
            writeSpecial(Numpad[8]);
            return;
          case '9':
            writeSpecial(Numpad[9]);
            return;
          case '.':
            writeSpecial(KPPeriod);
            return;
          case '-':
          case 31:
            writeSpecial(KPMinus);
            return;
          case '+':
            writeSpecial(KPComma);
            return;
          case 10:
            writeSpecial(KPEnter);
            return;
          case '/':
            writeSpecial(PF2);
            return;
          case '*':
            writeSpecial(PF3);
            return;
          default:
            break;
        }
    }

    // FIXME: not used?
    String fmap[];
    int xind;
    xind = 0;
    fmap = FunctionKey;
    if (shift) {
      fmap = FunctionKeyShift;
      xind = 1;
    }
    if (control) {
      fmap = FunctionKeyCtrl;
      xind = 2;
    }
    if (alt) {
      fmap = FunctionKeyAlt;
      xind = 3;
    }

    if (keyCode == KeyEvent.VK_ESCAPE) {
      writeSpecial(Escape[xind]);
      return;
    }

    if ((modifiers & VDUInput.KEY_ACTION) != 0)
      switch (keyCode) {
        case KeyEvent.VK_NUMPAD0:
          writeSpecial(Numpad[0]);
          return;
        case KeyEvent.VK_NUMPAD1:
          writeSpecial(Numpad[1]);
          return;
        case KeyEvent.VK_NUMPAD2:
          writeSpecial(Numpad[2]);
          return;
        case KeyEvent.VK_NUMPAD3:
          writeSpecial(Numpad[3]);
          return;
        case KeyEvent.VK_NUMPAD4:
          writeSpecial(Numpad[4]);
          return;
        case KeyEvent.VK_NUMPAD5:
          writeSpecial(Numpad[5]);
          return;
        case KeyEvent.VK_NUMPAD6:
          writeSpecial(Numpad[6]);
          return;
        case KeyEvent.VK_NUMPAD7:
          writeSpecial(Numpad[7]);
          return;
        case KeyEvent.VK_NUMPAD8:
          writeSpecial(Numpad[8]);
          return;
        case KeyEvent.VK_NUMPAD9:
          writeSpecial(Numpad[9]);
          return;
        case KeyEvent.VK_DECIMAL:
          writeSpecial(NUMDot[xind]);
          return;
        case KeyEvent.VK_ADD:
          writeSpecial(NUMPlus[xind]);
          return;
      }

    if (!((keyChar == 8) || (keyChar == 127) || (keyChar == '\r') || (keyChar == '\n'))) {
      write("" + keyChar);
      return;
    }
  }

  private void handle_dcs(String dcs) {
    System.out.println("DCS: " + dcs);
  }

  private void handle_osc(String osc) {
    System.out.println("OSC: " + osc);
  }

  private final static char unimap[] = {
    //#
    //#    Name:     cp437_DOSLatinUS to Unicode table
    //#    Unicode version: 1.1
    //#    Table version: 1.1
    //#    Table format:  Format A
    //#    Date:          03/31/95
    //#    Authors:       Michel Suignard <michelsu@microsoft.com>
    //#                   Lori Hoerth <lorih@microsoft.com>
    //#    General notes: none
    //#
    //#    Format: Three tab-separated columns
    //#        Column #1 is the cp1255_WinHebrew code (in hex)
    //#        Column #2 is the Unicode (in hex as 0xXXXX)
    //#        Column #3 is the Unicode name (follows a comment sign, '#')
    //#
    //#    The entries are in cp437_DOSLatinUS order
    //#

    0x0000, // #NULL
    0x0001, // #START OF HEADING
    0x0002, // #START OF TEXT
    0x0003, // #END OF TEXT
    0x0004, // #END OF TRANSMISSION
    0x0005, // #ENQUIRY
    0x0006, // #ACKNOWLEDGE
    0x0007, // #BELL
    0x0008, // #BACKSPACE
    0x0009, // #HORIZONTAL TABULATION
    0x000a, // #LINE FEED
    0x000b, // #VERTICAL TABULATION
    0x000c, // #FORM FEED
    0x000d, // #CARRIAGE RETURN
    0x000e, // #SHIFT OUT
    0x000f, // #SHIFT IN
    0x0010, // #DATA LINK ESCAPE
    0x0011, // #DEVICE CONTROL ONE
    0x0012, // #DEVICE CONTROL TWO
    0x0013, // #DEVICE CONTROL THREE
    0x0014, // #DEVICE CONTROL FOUR
    0x0015, // #NEGATIVE ACKNOWLEDGE
    0x0016, // #SYNCHRONOUS IDLE
    0x0017, // #END OF TRANSMISSION BLOCK
    0x0018, // #CANCEL
    0x0019, // #END OF MEDIUM
    0x001a, // #SUBSTITUTE
    0x001b, // #ESCAPE
    0x001c, // #FILE SEPARATOR
    0x001d, // #GROUP SEPARATOR
    0x001e, // #RECORD SEPARATOR
    0x001f, // #UNIT SEPARATOR
    0x0020, // #SPACE
    0x0021, // #EXCLAMATION MARK
    0x0022, // #QUOTATION MARK
    0x0023, // #NUMBER SIGN
    0x0024, // #DOLLAR SIGN
    0x0025, // #PERCENT SIGN
    0x0026, // #AMPERSAND
    0x0027, // #APOSTROPHE
    0x0028, // #LEFT PARENTHESIS
    0x0029, // #RIGHT PARENTHESIS
    0x002a, // #ASTERISK
    0x002b, // #PLUS SIGN
    0x002c, // #COMMA
    0x002d, // #HYPHEN-MINUS
    0x002e, // #FULL STOP
    0x002f, // #SOLIDUS
    0x0030, // #DIGIT ZERO
    0x0031, // #DIGIT ONE
    0x0032, // #DIGIT TWO
    0x0033, // #DIGIT THREE
    0x0034, // #DIGIT FOUR
    0x0035, // #DIGIT FIVE
    0x0036, // #DIGIT SIX
    0x0037, // #DIGIT SEVEN
    0x0038, // #DIGIT EIGHT
    0x0039, // #DIGIT NINE
    0x003a, // #COLON
    0x003b, // #SEMICOLON
    0x003c, // #LESS-THAN SIGN
    0x003d, // #EQUALS SIGN
    0x003e, // #GREATER-THAN SIGN
    0x003f, // #QUESTION MARK
    0x0040, // #COMMERCIAL AT
    0x0041, // #LATIN CAPITAL LETTER A
    0x0042, // #LATIN CAPITAL LETTER B
    0x0043, // #LATIN CAPITAL LETTER C
    0x0044, // #LATIN CAPITAL LETTER D
    0x0045, // #LATIN CAPITAL LETTER E
    0x0046, // #LATIN CAPITAL LETTER F
    0x0047, // #LATIN CAPITAL LETTER G
    0x0048, // #LATIN CAPITAL LETTER H
    0x0049, // #LATIN CAPITAL LETTER I
    0x004a, // #LATIN CAPITAL LETTER J
    0x004b, // #LATIN CAPITAL LETTER K
    0x004c, // #LATIN CAPITAL LETTER L
    0x004d, // #LATIN CAPITAL LETTER M
    0x004e, // #LATIN CAPITAL LETTER N
    0x004f, // #LATIN CAPITAL LETTER O
    0x0050, // #LATIN CAPITAL LETTER P
    0x0051, // #LATIN CAPITAL LETTER Q
    0x0052, // #LATIN CAPITAL LETTER R
    0x0053, // #LATIN CAPITAL LETTER S
    0x0054, // #LATIN CAPITAL LETTER T
    0x0055, // #LATIN CAPITAL LETTER U
    0x0056, // #LATIN CAPITAL LETTER V
    0x0057, // #LATIN CAPITAL LETTER W
    0x0058, // #LATIN CAPITAL LETTER X
    0x0059, // #LATIN CAPITAL LETTER Y
    0x005a, // #LATIN CAPITAL LETTER Z
    0x005b, // #LEFT SQUARE BRACKET
    0x005c, // #REVERSE SOLIDUS
    0x005d, // #RIGHT SQUARE BRACKET
    0x005e, // #CIRCUMFLEX ACCENT
    0x005f, // #LOW LINE
    0x0060, // #GRAVE ACCENT
    0x0061, // #LATIN SMALL LETTER A
    0x0062, // #LATIN SMALL LETTER B
    0x0063, // #LATIN SMALL LETTER C
    0x0064, // #LATIN SMALL LETTER D
    0x0065, // #LATIN SMALL LETTER E
    0x0066, // #LATIN SMALL LETTER F
    0x0067, // #LATIN SMALL LETTER G
    0x0068, // #LATIN SMALL LETTER H
    0x0069, // #LATIN SMALL LETTER I
    0x006a, // #LATIN SMALL LETTER J
    0x006b, // #LATIN SMALL LETTER K
    0x006c, // #LATIN SMALL LETTER L
    0x006d, // #LATIN SMALL LETTER M
    0x006e, // #LATIN SMALL LETTER N
    0x006f, // #LATIN SMALL LETTER O
    0x0070, // #LATIN SMALL LETTER P
    0x0071, // #LATIN SMALL LETTER Q
    0x0072, // #LATIN SMALL LETTER R
    0x0073, // #LATIN SMALL LETTER S
    0x0074, // #LATIN SMALL LETTER T
    0x0075, // #LATIN SMALL LETTER U
    0x0076, // #LATIN SMALL LETTER V
    0x0077, // #LATIN SMALL LETTER W
    0x0078, // #LATIN SMALL LETTER X
    0x0079, // #LATIN SMALL LETTER Y
    0x007a, // #LATIN SMALL LETTER Z
    0x007b, // #LEFT CURLY BRACKET
    0x007c, // #VERTICAL LINE
    0x007d, // #RIGHT CURLY BRACKET
    0x007e, // #TILDE
    0x007f, // #DELETE
    0x00c7, // #LATIN CAPITAL LETTER C WITH CEDILLA
    0x00fc, // #LATIN SMALL LETTER U WITH DIAERESIS
    0x00e9, // #LATIN SMALL LETTER E WITH ACUTE
    0x00e2, // #LATIN SMALL LETTER A WITH CIRCUMFLEX
    0x00e4, // #LATIN SMALL LETTER A WITH DIAERESIS
    0x00e0, // #LATIN SMALL LETTER A WITH GRAVE
    0x00e5, // #LATIN SMALL LETTER A WITH RING ABOVE
    0x00e7, // #LATIN SMALL LETTER C WITH CEDILLA
    0x00ea, // #LATIN SMALL LETTER E WITH CIRCUMFLEX
    0x00eb, // #LATIN SMALL LETTER E WITH DIAERESIS
    0x00e8, // #LATIN SMALL LETTER E WITH GRAVE
    0x00ef, // #LATIN SMALL LETTER I WITH DIAERESIS
    0x00ee, // #LATIN SMALL LETTER I WITH CIRCUMFLEX
    0x00ec, // #LATIN SMALL LETTER I WITH GRAVE
    0x00c4, // #LATIN CAPITAL LETTER A WITH DIAERESIS
    0x00c5, // #LATIN CAPITAL LETTER A WITH RING ABOVE
    0x00c9, // #LATIN CAPITAL LETTER E WITH ACUTE
    0x00e6, // #LATIN SMALL LIGATURE AE
    0x00c6, // #LATIN CAPITAL LIGATURE AE
    0x00f4, // #LATIN SMALL LETTER O WITH CIRCUMFLEX
    0x00f6, // #LATIN SMALL LETTER O WITH DIAERESIS
    0x00f2, // #LATIN SMALL LETTER O WITH GRAVE
    0x00fb, // #LATIN SMALL LETTER U WITH CIRCUMFLEX
    0x00f9, // #LATIN SMALL LETTER U WITH GRAVE
    0x00ff, // #LATIN SMALL LETTER Y WITH DIAERESIS
    0x00d6, // #LATIN CAPITAL LETTER O WITH DIAERESIS
    0x00dc, // #LATIN CAPITAL LETTER U WITH DIAERESIS
    0x00a2, // #CENT SIGN
    0x00a3, // #POUND SIGN
    0x00a5, // #YEN SIGN
    0x20a7, // #PESETA SIGN
    0x0192, // #LATIN SMALL LETTER F WITH HOOK
    0x00e1, // #LATIN SMALL LETTER A WITH ACUTE
    0x00ed, // #LATIN SMALL LETTER I WITH ACUTE
    0x00f3, // #LATIN SMALL LETTER O WITH ACUTE
    0x00fa, // #LATIN SMALL LETTER U WITH ACUTE
    0x00f1, // #LATIN SMALL LETTER N WITH TILDE
    0x00d1, // #LATIN CAPITAL LETTER N WITH TILDE
    0x00aa, // #FEMININE ORDINAL INDICATOR
    0x00ba, // #MASCULINE ORDINAL INDICATOR
    0x00bf, // #INVERTED QUESTION MARK
    0x2310, // #REVERSED NOT SIGN
    0x00ac, // #NOT SIGN
    0x00bd, // #VULGAR FRACTION ONE HALF
    0x00bc, // #VULGAR FRACTION ONE QUARTER
    0x00a1, // #INVERTED EXCLAMATION MARK
    0x00ab, // #LEFT-POINTING DOUBLE ANGLE QUOTATION MARK
    0x00bb, // #RIGHT-POINTING DOUBLE ANGLE QUOTATION MARK
    0x2591, // #LIGHT SHADE
    0x2592, // #MEDIUM SHADE
    0x2593, // #DARK SHADE
    0x2502, // #BOX DRAWINGS LIGHT VERTICAL
    0x2524, // #BOX DRAWINGS LIGHT VERTICAL AND LEFT
    0x2561, // #BOX DRAWINGS VERTICAL SINGLE AND LEFT DOUBLE
    0x2562, // #BOX DRAWINGS VERTICAL DOUBLE AND LEFT SINGLE
    0x2556, // #BOX DRAWINGS DOWN DOUBLE AND LEFT SINGLE
    0x2555, // #BOX DRAWINGS DOWN SINGLE AND LEFT DOUBLE
    0x2563, // #BOX DRAWINGS DOUBLE VERTICAL AND LEFT
    0x2551, // #BOX DRAWINGS DOUBLE VERTICAL
    0x2557, // #BOX DRAWINGS DOUBLE DOWN AND LEFT
    0x255d, // #BOX DRAWINGS DOUBLE UP AND LEFT
    0x255c, // #BOX DRAWINGS UP DOUBLE AND LEFT SINGLE
    0x255b, // #BOX DRAWINGS UP SINGLE AND LEFT DOUBLE
    0x2510, // #BOX DRAWINGS LIGHT DOWN AND LEFT
    0x2514, // #BOX DRAWINGS LIGHT UP AND RIGHT
    0x2534, // #BOX DRAWINGS LIGHT UP AND HORIZONTAL
    0x252c, // #BOX DRAWINGS LIGHT DOWN AND HORIZONTAL
    0x251c, // #BOX DRAWINGS LIGHT VERTICAL AND RIGHT
    0x2500, // #BOX DRAWINGS LIGHT HORIZONTAL
    0x253c, // #BOX DRAWINGS LIGHT VERTICAL AND HORIZONTAL
    0x255e, // #BOX DRAWINGS VERTICAL SINGLE AND RIGHT DOUBLE
    0x255f, // #BOX DRAWINGS VERTICAL DOUBLE AND RIGHT SINGLE
    0x255a, // #BOX DRAWINGS DOUBLE UP AND RIGHT
    0x2554, // #BOX DRAWINGS DOUBLE DOWN AND RIGHT
    0x2569, // #BOX DRAWINGS DOUBLE UP AND HORIZONTAL
    0x2566, // #BOX DRAWINGS DOUBLE DOWN AND HORIZONTAL
    0x2560, // #BOX DRAWINGS DOUBLE VERTICAL AND RIGHT
    0x2550, // #BOX DRAWINGS DOUBLE HORIZONTAL
    0x256c, // #BOX DRAWINGS DOUBLE VERTICAL AND HORIZONTAL
    0x2567, // #BOX DRAWINGS UP SINGLE AND HORIZONTAL DOUBLE
    0x2568, // #BOX DRAWINGS UP DOUBLE AND HORIZONTAL SINGLE
    0x2564, // #BOX DRAWINGS DOWN SINGLE AND HORIZONTAL DOUBLE
    0x2565, // #BOX DRAWINGS DOWN DOUBLE AND HORIZONTAL SINGLE
    0x2559, // #BOX DRAWINGS UP DOUBLE AND RIGHT SINGLE
    0x2558, // #BOX DRAWINGS UP SINGLE AND RIGHT DOUBLE
    0x2552, // #BOX DRAWINGS DOWN SINGLE AND RIGHT DOUBLE
    0x2553, // #BOX DRAWINGS DOWN DOUBLE AND RIGHT SINGLE
    0x256b, // #BOX DRAWINGS VERTICAL DOUBLE AND HORIZONTAL SINGLE
    0x256a, // #BOX DRAWINGS VERTICAL SINGLE AND HORIZONTAL DOUBLE
    0x2518, // #BOX DRAWINGS LIGHT UP AND LEFT
    0x250c, // #BOX DRAWINGS LIGHT DOWN AND RIGHT
    0x2588, // #FULL BLOCK
    0x2584, // #LOWER HALF BLOCK
    0x258c, // #LEFT HALF BLOCK
    0x2590, // #RIGHT HALF BLOCK
    0x2580, // #UPPER HALF BLOCK
    0x03b1, // #GREEK SMALL LETTER ALPHA
    0x00df, // #LATIN SMALL LETTER SHARP S
    0x0393, // #GREEK CAPITAL LETTER GAMMA
    0x03c0, // #GREEK SMALL LETTER PI
    0x03a3, // #GREEK CAPITAL LETTER SIGMA
    0x03c3, // #GREEK SMALL LETTER SIGMA
    0x00b5, // #MICRO SIGN
    0x03c4, // #GREEK SMALL LETTER TAU
    0x03a6, // #GREEK CAPITAL LETTER PHI
    0x0398, // #GREEK CAPITAL LETTER THETA
    0x03a9, // #GREEK CAPITAL LETTER OMEGA
    0x03b4, // #GREEK SMALL LETTER DELTA
    0x221e, // #INFINITY
    0x03c6, // #GREEK SMALL LETTER PHI
    0x03b5, // #GREEK SMALL LETTER EPSILON
    0x2229, // #INTERSECTION
    0x2261, // #IDENTICAL TO
    0x00b1, // #PLUS-MINUS SIGN
    0x2265, // #GREATER-THAN OR EQUAL TO
    0x2264, // #LESS-THAN OR EQUAL TO
    0x2320, // #TOP HALF INTEGRAL
    0x2321, // #BOTTOM HALF INTEGRAL
    0x00f7, // #DIVISION SIGN
    0x2248, // #ALMOST EQUAL TO
    0x00b0, // #DEGREE SIGN
    0x2219, // #BULLET OPERATOR
    0x00b7, // #MIDDLE DOT
    0x221a, // #SQUARE ROOT
    0x207f, // #SUPERSCRIPT LATIN SMALL LETTER N
    0x00b2, // #SUPERSCRIPT TWO
    0x25a0, // #BLACK SQUARE
    0x00a0, // #NO-BREAK SPACE
  };

  public char map_cp850_unicode(char x) {
    if (x >= 0x100)
      return x;
    return unimap[x];
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

  private void putChar(char c, boolean doshowcursor) {
    int rows = getRows(); //statusline
    int columns = getColumns();
    int tm = getTopMargin();
    int bm = getBottomMargin();
    // byte msg[];
    boolean mapped = false;

    if (debug > 4) System.out.println("putChar(" + c + " [" + ((int) c) + "]) at R=" + R + " , C=" + C + ", columns=" + columns + ", rows=" + rows);
    markLine(R, 1);
    if (c > 255) {
      if (debug > 0)
        System.out.println("char > 255:" + (int) c);
      //return;
    }


    switch (term_state) {
      case TSTATE_DATA:
        if (!useibmcharset) {
          boolean doneflag = true;
          switch (c) {
            case OSC:
              osc = "";
              term_state = TSTATE_OSC;
              break;
            case RI:
              if (R > tm)
                R--;
              else
                insertLine(R, 1, SCROLL_DOWN);
              if (debug > 1)
                System.out.println("RI");
              break;
            case IND:
              if (debug > 2)
                System.out.println("IND at " + R + ", tm is " + tm + ", bm is " + bm);
              if (R == bm || R == rows - 1)
                insertLine(R, 1, SCROLL_UP);
              else
                R++;
              if (debug > 1)
                System.out.println("IND (at " + R + " )");
              break;
            case NEL:
              if (R == bm || R == rows - 1)
                insertLine(R, 1, SCROLL_UP);
              else
                R++;
              C = 0;
              if (debug > 1)
                System.out.println("NEL (at " + R + " )");
              break;
            case HTS:
              Tabs[C] = 1;
              if (debug > 1)
                System.out.println("HTS");
              break;
            case DCS:
              dcs = "";
              term_state = TSTATE_DCS;
              break;
            default:
              doneflag = false;
              break;
          }
          if (doneflag) break;
        }
        switch (c) {
          case SS3:
            onegl = 3;
            break;
          case SS2:
            onegl = 2;
            break;
          case CSI: // should be in the 8bit section, but some BBS use this
            DCEvar = 0;
            DCEvars[0] = 0;
            DCEvars[1] = 0;
            DCEvars[2] = 0;
            DCEvars[3] = 0;
            term_state = TSTATE_CSI;
            break;
          case ESC:
            term_state = TSTATE_ESC;
            lastwaslf = 0;
            break;
          case 5:
            write(answerBack, false);
            break;
          case 12:
            deleteArea(0, 0, columns, rows, attributes);
            C = R = 0;
            break;
          case '\b': 
            C--;
            if (C < 0)
              C = 0;
            lastwaslf = 0;
            break;
          case '\t':
            do {
              // Don't overwrite or insert! TABS are not destructive, but movement!
              C++;
            } while (C < columns && (Tabs[C] == 0));
            lastwaslf = 0;
            break;
          case '\r':
            C = 0;
            break;
          case '\n':
            if (debug > 3)
              System.out.println("R= " + R + ", bm " + bm + ", tm=" + tm + ", rows=" + rows);
            if (!vms) {
              if (lastwaslf != 0 && lastwaslf != c)   //  Ray: I do not understand this logic.
                break;
              lastwaslf = c;
            }
            if (R == bm || R >= rows - 1)
              insertLine(R, 1, SCROLL_UP);
            else
              R++;
            break;
          case 7:
            beep();
            break;
          case 'u':
            gl = 1;
            usedcharsets = true;
            break;
          case 'u':
            gl = 0;
            usedcharsets = true;
            break;
          default:
            {
              int thisgl = gl;

              if (onegl >= 0) {
                thisgl = onegl;
                onegl = -1;
              }
              lastwaslf = 0;
              if (c < 32) {
                if (c != 0)
                  if (debug > 0)
                    System.out.println("TSTATE_DATA char: " + ((int) c));
                if (c == 0)
                  break;
              }
              if (C >= columns) {
                if (wraparound) {
                  if (R < rows - 1)
                    R++;
                  else
                    insertLine(R, 1, SCROLL_UP);
                  C = 0;
                } else {
                  // cursor stays on last character.
                  C = columns - 1;
                }
              }

              // Mapping if DEC Special is chosen charset
              if (usedcharsets) {
                if (c >= 'u' && c <= 'u') {
                  switch (gx[thisgl]) {
                    case '0':
                      // Remap SCOANSI line drawing to VT100 line drawing chars
                      // for our SCO using customers.
                      if (terminalID.equals("scoansi") || terminalID.equals("ansi")) {
                        for (int i = 0; i < scoansi_acs.length(); i += 2) {
                          if (c == scoansi_acs.charAt(i)) {
                            c = scoansi_acs.charAt(i + 1);
                            break;
                          }
                        }
                      }
                      if (c >= 'u' && c <= 'u') {
                        c = DECSPECIAL[(short) c - 0x5f];
                        mapped = true;
                      }
                      break;
                    case '<': // 'user preferred' is currently 'ISO Latin-1 suppl
                      c = (char) (((int) c & 0x7f) | 0x80);
                      mapped = true;
                      break;
                    case 'A':
                    case 'B': // Latin-1 , ASCII -> fall through
                      mapped = true;
                      break;
                    default:
                      System.out.println("Unsupported GL mapping: " + gx[thisgl]);
                      break;
                  }
                }
                if (!mapped && (c >= 'u' && c <= 'u')) {
                  switch (gx[gr]) {
                    case '0':
                      if (c >= 'u' && c <= 'u') {
                        c = DECSPECIAL[c - 'u'];
                        mapped = true;
                      }
                      break;
                    case '<':
                    case 'A':
                    case 'B':
                      mapped = true;
                      break;
                    default:
                      System.out.println("Unsupported GR mapping: " + gx[gr]);
                      break;
                  }
                }
              }
              if (!mapped && useibmcharset)
                c = map_cp850_unicode(c);

              if (insertmode == 1) {
                insertChar(C, R, c, attributes);
              } else {
                putChar(C, R, c, attributes);
              }
              C++;
              break;
            }
        }
        break;
      case TSTATE_OSC:
        if ((c < 0x20) && (c != ESC)) {// NP - No printing character
          handle_osc(osc);
          term_state = TSTATE_DATA;
          break;
        }
        //but check for vt102 ESC \
        if (c == '\\' && osc.charAt(osc.length() - 1) == ESC) {
          handle_osc(osc);
          term_state = TSTATE_DATA;
          break;
        }
        osc = osc + c;
        break;
      case TSTATE_ESCSPACE:
        term_state = TSTATE_DATA;
        switch (c) {
          case 'F': 
            output8bit = false;
            break;
          case 'G': 
            output8bit = true;
            break;
          default:
            System.out.println("ESC <space> " + c + " unhandled.");
        }
        break;
      case TSTATE_ESC:
        term_state = TSTATE_DATA;
        switch (c) {
          case ' ':
            term_state = TSTATE_ESCSPACE;
            break;
          case '#':
            term_state = TSTATE_ESCSQUARE;
            break;
          case 'c':
            gx[0] = 'B';
            gx[1] = '0';
            gx[2] = 'B';
            gx[3] = 'B';
            gl = 0;  // default GL to G0
            gr = 1;  // default GR to G1
            int nw = getColumns();
            if (nw < 132) nw = 132;
            Tabs = new byte[nw];
            for (int i = 0; i < nw; i += 8) {
              Tabs[i] = 1;
            }
            break;
          case '[':
            DCEvar = 0;
            DCEvars[0] = 0;
            DCEvars[1] = 0;
            DCEvars[2] = 0;
            DCEvars[3] = 0;
            term_state = TSTATE_CSI;
            break;
          case ']':
            osc = "";
            term_state = TSTATE_OSC;
            break;
          case 'P':
            dcs = "";
            term_state = TSTATE_DCS;
            break;
          case 'A':
            R--;
            if (R < 0) R = 0;
            break;
          case 'B':
            R++;
            if (R > rows - 1) R = rows - 1;
            break;
          case 'C':
            C++;
            if (C >= columns) C = columns - 1;
            break;
          case 'I': // RI
            insertLine(R, 1, SCROLL_DOWN);
            break;
          case 'E':
            if (R == bm || R == rows - 1)
              insertLine(R, 1, SCROLL_UP);
            else
              R++;
            C = 0;
            if (debug > 1)
              System.out.println("ESC E (at " + R + ")");
            break;
          case 'D':
            if (R == bm || R == rows - 1)
              insertLine(R, 1, SCROLL_UP);
            else
              R++;
            if (debug > 1)
              System.out.println("ESC D (at " + R + " )");
            break;
          case 'J':
            if (R < rows - 1)
              deleteArea(0, R + 1, columns, rows - R - 1, attributes);
            if (C < columns - 1)
              deleteArea(C, R, columns - C, 1, attributes);
            break;
          case 'K':
            if (C < columns - 1)
              deleteArea(C, R, columns - C, 1, attributes);
            break;
          case 'M': // RI
            System.out.println("ESC M : R is "+R+", tm is "+tm+", bm is "+bm);
            if (R > bm) // outside scrolling region
              break;
            if (R > tm) { // just go up 1 line.
              R--;
            } else { // scroll down
              insertLine(R, 1, SCROLL_DOWN);
            }
            if (debug > 2)
              System.out.println("ESC M ");
            break;
          case 'H':
            if (debug > 1)
              System.out.println("ESC H at " + C);
            if (C >= columns)
              C = columns - 1;
            Tabs[C] = 1;
            break;
          case 'N': // SS2
            onegl = 2;
            break;
          case 'O': // SS3
            onegl = 3;
            break;
          case '=':
            if (debug > 0)
              System.out.println("ESC =");
            keypadmode = true;
            break;
          case '<':
            vt52mode = false;
            break;
          case '>':
            if (debug > 0)
              System.out.println("ESC >");
            keypadmode = false;
            break;
          case '7':
            Sc = C;
            Sr = R;
            Sgl = gl;
            Sgr = gr;
            Sa = attributes;
            Sgx = new char[4];
            for (int i = 0; i < 4; i++) Sgx[i] = gx[i];
            Stm = getTopMargin();
            Sbm = getBottomMargin();
            if (debug > 1)
              System.out.println("ESC 7");
            break;
          case '8':
            C = Sc;
            R = Sr;
            gl = Sgl;
            gr = Sgr;
            for (int i = 0; i < 4; i++) gx[i] = Sgx[i];
            setTopMargin(Stm);
            setBottomMargin(Sbm);
            attributes = Sa;
            if (debug > 1)
              System.out.println("ESC 8");
            break;
          case '(': 
            term_state = TSTATE_SETG0;
            usedcharsets = true;
            break;
          case ')': 
            term_state = TSTATE_SETG1;
            usedcharsets = true;
            break;
          case '*': 
            term_state = TSTATE_SETG2;
            usedcharsets = true;
            break;
          case '+': 
            term_state = TSTATE_SETG3;
            usedcharsets = true;
            break;
          case '~': 
            gr = 1;
            usedcharsets = true;
            break;
          case 'n': 
            gl = 2;
            usedcharsets = true;
            break;
          case '}':
            gr = 2;
            usedcharsets = true;
            break;
          case 'o':
            gl = 3;
            usedcharsets = true;
            break;
          case '|':
            gr = 3;
            usedcharsets = true;
            break;
          case 'Y':
            term_state = TSTATE_VT52Y;
            break;
          default:
            System.out.println("ESC unknown letter: " + c + " (" + ((int) c) + ")");
            break;
        }
        break;
      case TSTATE_VT52X:
        C = c - 37;
        term_state = TSTATE_VT52Y;
        break;
      case TSTATE_VT52Y:
        R = c - 37;
        term_state = TSTATE_DATA;
        break;
      case TSTATE_SETG0:
        if (c != '0' && c != 'A' && c != 'B' && c != '<')
          System.out.println("ESC ( " + c + ": G0 char set?  (" + ((int) c) + ")");
        else {
          if (debug > 2) System.out.println("ESC ( : G0 char set  (" + c + " " + ((int) c) + ")");
          gx[0] = c;
        }
        term_state = TSTATE_DATA;
        break;
      case TSTATE_SETG1:
        if (c != '0' && c != 'A' && c != 'B' && c != '<') {
          System.out.println("ESC ) " + c + " (" + ((int) c) + ") :G1 char set?");
        } else {
          if (debug > 2) System.out.println("ESC ) :G1 char set  (" + c + " " + ((int) c) + ")");
          gx[1] = c;
        }
        term_state = TSTATE_DATA;
        break;
      case TSTATE_SETG2:
        if (c != '0' && c != 'A' && c != 'B' && c != '<')
          System.out.println("ESC*:G2 char set?  (" + ((int) c) + ")");
        else {
          if (debug > 2) System.out.println("ESC*:G2 char set  (" + c + " " + ((int) c) + ")");
          gx[2] = c;
        }
        term_state = TSTATE_DATA;
        break;
      case TSTATE_SETG3:
        if (c != '0' && c != 'A' && c != 'B' && c != '<')
          System.out.println("ESC+:G3 char set?  (" + ((int) c) + ")");
        else {
          if (debug > 2) System.out.println("ESC+:G3 char set  (" + c + " " + ((int) c) + ")");
          gx[3] = c;
        }
        term_state = TSTATE_DATA;
        break;
      case TSTATE_ESCSQUARE:
        switch (c) {
          case '8':
            for (int i = 0; i < columns; i++)
              for (int j = 0; j < rows; j++)
                putChar(i, j, 'E', 0);
            break;
          default:
            System.out.println("ESC # " + c + " not supported.");
            break;
        }
        term_state = TSTATE_DATA;
        break;
      case TSTATE_DCS:
        if (c == '\\' && dcs.charAt(dcs.length() - 1) == ESC) {
          handle_dcs(dcs);
          term_state = TSTATE_DATA;
          break;
        }
        dcs = dcs + c;
        break;

      case TSTATE_DCEQ:
        term_state = TSTATE_DATA;
        switch (c) {
          case '0':
          case '1':
          case '2':
          case '3':
          case '4':
          case '5':
          case '6':
          case '7':
          case '8':
          case '9':
            DCEvars[DCEvar] = DCEvars[DCEvar] * 10 + ((int) c) - 48;
            term_state = TSTATE_DCEQ;
            break;
          case ';':
            DCEvar++;
            DCEvars[DCEvar] = 0;
            term_state = TSTATE_DCEQ;
            break;
          case 's': // XTERM_SAVE missing!
            if (true || debug > 1)
              System.out.println("ESC [ ? " + DCEvars[0] + " s unimplemented!");
            break;
          case 'r': // XTERM_RESTORE
            if (true || debug > 1)
              System.out.println("ESC [ ? " + DCEvars[0] + " r");
            for (int i = 0; i <= DCEvar; i++) {
              switch (DCEvars[i]) {
                case 3: 
                  setScreenSize(80, getRows(), true);
                  break;
                case 4: 
                  break;
                case 5: 
                  break;
                case 6: 
                  moveoutsidemargins = true;
                  break;
                case 7: 
                  wraparound = false;
                  break;
                case 12:
                  break;
                case 9: 	
                case 1000:	
                case 1001:
                case 1002:
                case 1003:
                  mouserpt = DCEvars[i];
                  break;
                default:
                  System.out.println("ESC [ ? " + DCEvars[0] + " r, unimplemented!");
              }
            }
            break;
          case 'h': // DECSET
            if (debug > 0)
              System.out.println("ESC [ ? " + DCEvars[0] + " h");
            for (int i = 0; i <= DCEvar; i++) {
              switch (DCEvars[i]) {
                case 1:  
                  KeyUp[0] = "001bOA";
                  KeyDown[0] = "001bOB";
                  KeyRight[0] = "001bOC";
                  KeyLeft[0] = "001bOD";
                  break;
                case 2: 
                  vt52mode = false;
                  break;
                case 3: 
                  setScreenSize(132, getRows(), true);
                  break;
                case 6: 
                  moveoutsidemargins = false;
                  break;
                case 7: 
                  wraparound = true;
                  break;
                case 25: 
                  showCursor(true);
                  break;
                case 9: 	
                case 1000:	
                case 1001:
                case 1002:
                case 1003:
                  mouserpt = DCEvars[i];
                  break;

                default:
                  System.out.println("ESC [ ? " + DCEvars[0] + " h, unsupported.");
                  break;
              }
            }
            break;
          case 'i': // DEC Printer Control, autoprint, echo screenchars to printer
            // This is different to CSI i!
            // Also: "Autoprint prints a final display line only when the
            // cursor is moved off the line by an autowrap or LF, FF, or
            // VT (otherwise do not print the line)."
            switch (DCEvars[0]) {
              case 1:
                if (debug > 1)
                  System.out.println("CSI ? 1 i : Print line containing cursor");
                break;
              case 4:
                if (debug > 1)
                  System.out.println("CSI ? 4 i : Start passthrough printing");
                break;
              case 5:
                if (debug > 1)
                  System.out.println("CSI ? 4 i : Stop passthrough printing");
                break;
            }
            break;
          case 'l':	//DECRST
            if (debug > 0)
              System.out.println("ESC [ ? " + DCEvars[0] + " l");
            for (int i = 0; i <= DCEvar; i++) {
              switch (DCEvars[i]) {
                case 1:  
                  KeyUp[0] = "001b[A";
                  KeyDown[0] = "001b[B";
                  KeyRight[0] = "001b[C";
                  KeyLeft[0] = "001b[D";
                  break;
                case 2: 
                  vt52mode = true;
                  break;
                case 3: 
                  setScreenSize(80, getRows(), true);
                  break;
                case 6: 
                  moveoutsidemargins = true;
                  break;
                case 7: 
                  wraparound = false;
                  break;
                case 25: 
                  showCursor(false);
                  break;
                case 9: 	
                case 1000:	
                case 1001:
                case 1002:
                case 1003:
                  mouserpt = 0;
                  break;
                default:
                  System.out.println("ESC [ ? " + DCEvars[0] + " l, unsupported.");
                  break;
              }
            }
            break;
          case 'n':
            if (debug > 0)
              System.out.println("ESC [ ? " + DCEvars[0] + " n");
            switch (DCEvars[0]) {
              case 15:
                write(((char) ESC) + "[?13n", false);
                System.out.println("ESC[5n");
                break;
              default:
                System.out.println("ESC [ ? " + DCEvars[0] + " n, unsupported.");
                break;
            }
            break;
          default:
            System.out.println("ESC [ ? " + DCEvars[0] + " " + c + ", unsupported.");
            break;
        }
        break;
      case TSTATE_CSI_EX:
        term_state = TSTATE_DATA;
        switch (c) {
          case ESC:
            term_state = TSTATE_ESC;
            break;
          default:
            System.out.println("Unknown character ESC[! character is " + (int) c);
            break;
        }
        break;
      case TSTATE_CSI_TICKS:
        term_state = TSTATE_DATA;
        switch (c) {
          case 'p':
            System.out.println("Conformance level: " + DCEvars[0] + " (unsupported)," + DCEvars[1]);
            if (DCEvars[0] == 61) {
              output8bit = false;
              break;
            }
            if (DCEvars[1] == 1) {
              output8bit = false;
            } else {
              output8bit = true; 
            }
            break;
          default:
            System.out.println("Unknown ESC [...  \"" + c);
            break;
        }
        break;
      case TSTATE_CSI_EQUAL:
        term_state = TSTATE_DATA;
        switch (c) {
          case '0':
          case '1':
          case '2':
          case '3':
          case '4':
          case '5':
          case '6':
          case '7':
          case '8':
          case '9':
            DCEvars[DCEvar] = DCEvars[DCEvar] * 10 + ((int) c) - 48;
            term_state = TSTATE_CSI_EQUAL;
            break;
          case ';':
            DCEvar++;
            DCEvars[DCEvar] = 0;
            term_state = TSTATE_CSI_EQUAL;
            break;

          case 'F': 
	  {
	    int newcolor;

            System.out.println("ESC [ = "+DCEvars[0]+" F");

            attributes &= ~COLOR_FG;
	    newcolor =	((DCEvars[0] & 1) << 2)	|
	    		 (DCEvars[0] & 2)	|
	    		((DCEvars[0] & 4) >> 2) ;
            attributes |= (newcolor+1) << COLOR_FG_SHIFT;

	    break;
	  }
          case 'G': 
	  {
	    int newcolor;

            System.out.println("ESC [ = "+DCEvars[0]+" G");

            attributes &= ~COLOR_BG;
	    newcolor =	((DCEvars[0] & 1) << 2)	|
	    		 (DCEvars[0] & 2)	|
	    		((DCEvars[0] & 4) >> 2) ;
            attributes |= (newcolor+1) << COLOR_BG_SHIFT;
	    break;
          }

          default:
            System.out.print("Unknown ESC [ = ");
	    for (int i=0;i<=DCEvar;i++)
		System.out.print(DCEvars[i]+",");
	    System.out.println("" + c);
            break;
        }
        break;
      case TSTATE_CSI_DOLLAR:
        term_state = TSTATE_DATA;
        switch (c) {
          case '}':
            System.out.println("Active Status Display now " + DCEvars[0]);
            statusmode = DCEvars[0];
            break;
          case '~':
            System.out.println("Status Line mode now " + DCEvars[0]);
            break;
          default:
            System.out.println("UNKNOWN Status Display code " + c + ", with Pn=" + DCEvars[0]);
            break;
        }
        break;
      case TSTATE_CSI:
        term_state = TSTATE_DATA;
        switch (c) {
          case '"':
            term_state = TSTATE_CSI_TICKS;
            break;
          case '$':
            term_state = TSTATE_CSI_DOLLAR;
            break;
          case '=':
            term_state = TSTATE_CSI_EQUAL;
            break;
          case '!':
            term_state = TSTATE_CSI_EX;
            break;
          case '?':
            DCEvar = 0;
            DCEvars[0] = 0;
            term_state = TSTATE_DCEQ;
            break;
          case '0':
          case '1':
          case '2':
          case '3':
          case '4':
          case '5':
          case '6':
          case '7':
          case '8':
          case '9':
            DCEvars[DCEvar] = DCEvars[DCEvar] * 10 + ((int) c) - 48;
            term_state = TSTATE_CSI;
            break;
          case ';':
            DCEvar++;
            DCEvars[DCEvar] = 0;
            term_state = TSTATE_CSI;
            break;
          case 'c':

            String subcode = "";
            if (terminalID.equals("vt320")) subcode = "63;";
            if (terminalID.equals("vt220")) subcode = "62;";
            if (terminalID.equals("vt100")) subcode = "61;";
            write(((char) ESC) + "[?" + subcode + "1;2c", false);
            if (debug > 1)
              System.out.println("ESC [ " + DCEvars[0] + " c");
            break;
          case 'q':
            if (debug > 1)
              System.out.println("ESC [ " + DCEvars[0] + " q");
            break;
          case 'g':
            switch (DCEvars[0]) {
              case 3:
                Tabs = new byte[getColumns()];
                break;
              case 0:
                Tabs[C] = 0;
                break;
            }
            if (debug > 1)
              System.out.println("ESC [ " + DCEvars[0] + " g");
            break;
          case 'h':
            switch (DCEvars[0]) {
              case 4:
                insertmode = 1;
                break;
              case 20:
                System.out.println("Setting CRLF to TRUE");
                sendcrlf = true;
                break;
              default:
                System.out.println("unsupported: ESC [ " + DCEvars[0] + " h");
                break;
            }
            if (debug > 1)
              System.out.println("ESC [ " + DCEvars[0] + " h");
            break;
          case 'i': // Printer Controller mode.
            // "Transparent printing sends all output, except the CSI 4 i
            //  termination string, to the printer and not the screen,
            //  uses an 8-bit channel if no parity so NUL and DEL will be
            //  seen by the printer and by the termination recognizer code,
            //  and all translation and character set selections are
            //  bypassed."
            switch (DCEvars[0]) {
              case 0:
                if (debug > 1)
                  System.out.println("CSI 0 i:  Print Screen, not implemented.");
                break;
              case 4:
                if (debug > 1)
                  System.out.println("CSI 4 i:  Enable Transparent Printing, not implemented.");
                break;
              case 5:
                if (debug > 1)
                  System.out.println("CSI 4/5 i:  Disable Transparent Printing, not implemented.");
                break;
              default:
                System.out.println("ESC [ " + DCEvars[0] + " i, unimplemented!");
            }
            break;
          case 'l':
            switch (DCEvars[0]) {
              case 4:
                insertmode = 0;
                break;
              case 20:
                System.out.println("Setting CRLF to FALSE");
                sendcrlf = false;
                break;
              default:
                System.out.println("ESC [ " + DCEvars[0] + " l, unimplemented!");
                break;
            }
            break;
          case 'A': // CUU
            {
              int limit;
              if (R > bm)
                limit = bm + 1;
              else if (R >= tm) {
                limit = tm;
              } else
                limit = 0;
              if (DCEvars[0] == 0)
                R--;
              else
                R -= DCEvars[0];
              if (R < limit)
                R = limit;
              if (debug > 1)
                System.out.println("ESC [ " + DCEvars[0] + " A");
              break;
            }
          case 'B':	// CUD
            {
              int limit;
              if (R < tm)
                limit = tm - 1;
              else if (R <= bm) {
                limit = bm;
              } else
                limit = rows - 1;
              if (DCEvars[0] == 0)
                R++;
              else
                R += DCEvars[0];
              if (R > limit)
                R = limit;
              else {
                if (debug > 2) System.out.println("Not limited.");
              }
              if (debug > 2) System.out.println("to: " + R);
              if (debug > 1)
                System.out.println("ESC [ " + DCEvars[0] + " B (at C=" + C + ")");
              break;
            }
          case 'C':
            if (DCEvars[0] == 0)
              C++;
            else
              C += DCEvars[0];
            if (C > columns - 1)
              C = columns - 1;
            if (debug > 1)
              System.out.println("ESC [ " + DCEvars[0] + " C");
            break;
          case 'd': // CVA
            R = DCEvars[0];
            if (debug > 1)
              System.out.println("ESC [ " + DCEvars[0] + " d");
            break;
          case 'D':
            if (DCEvars[0] == 0)
              C--;
            else
              C -= DCEvars[0];
            if (C < 0) C = 0;
            if (debug > 1)
              System.out.println("ESC [ " + DCEvars[0] + " D");
            break;
          case 'r': // DECSTBM
            if (DCEvar > 0)   //  Ray:  Any argument is optional
            {
              R = DCEvars[1] - 1;
              if (R < 0)
                R = rows - 1;
              else if (R >= rows) {
                R = rows - 1;
              }
            } else
              R = rows - 1;
            setBottomMargin(R);
            if (R >= DCEvars[0]) {
              R = DCEvars[0] - 1;
              if (R < 0)
                R = 0;
            }
            setTopMargin(R);
            _SetCursor(0, 0);
            if (debug > 1)
              System.out.println("ESC [" + DCEvars[0] + " ; " + DCEvars[1] + " r");
            break;
          case 'G':  
            C = DCEvars[0];
            if (debug > 1) System.out.println("ESC [ " + DCEvars[0] + " G");
            break;
          case 'H':  
            _SetCursor(DCEvars[0] - 1, DCEvars[1] - 1);
            if (debug > 2) {
              System.out.println("ESC [ " + DCEvars[0] + ";" + DCEvars[1] + " H, moveoutsidemargins " + moveoutsidemargins);
              System.out.println("	-> R now " + R + ", C now " + C);
            }
            break;
          case 'f': 
            R = DCEvars[0] - 1;
            C = DCEvars[1] - 1;
            if (C < 0) C = 0;
            if (R < 0) R = 0;
            if (debug > 2)
              System.out.println("ESC [ " + DCEvars[0] + ";" + DCEvars[1] + " f");
            break;
          case 'S': 
            if (DCEvars[0] == 0)
              insertLine(rows - 1, SCROLL_UP);
            else
              insertLine(rows - 1, DCEvars[0], SCROLL_UP);
            break;
          case 'L':
            if (DCEvars[0] == 0)
              insertLine(R, SCROLL_DOWN);
            else
              insertLine(R, DCEvars[0], SCROLL_DOWN);
            if (debug > 1)
              System.out.println("ESC [ " + DCEvars[0] + "" + (c) + " (at R " + R + ")");
            break;
          case 'T': 
            if (DCEvars[0] == 0)
              insertLine(0, SCROLL_DOWN);
            else
              insertLine(0, DCEvars[0], SCROLL_DOWN);
            break;
          case 'M':
            if (debug > 1)
              System.out.println("ESC [ " + DCEvars[0] + "" + (c) + " at R=" + R);
            if (DCEvars[0] == 0)
              deleteLine(R);
            else
              for (int i = 0; i < DCEvars[0]; i++)
                deleteLine(R);
            break;
          case 'K':
            if (debug > 1)
              System.out.println("ESC [ " + DCEvars[0] + " K");
            switch (DCEvars[0]) {
              case 6: 
              case 0:
                if (C < columns - 1)
                  deleteArea(C, R, columns - C, 1, attributes);
                break;
              case 1:
                if (C > 0)
                  deleteArea(0, R, C + 1, 1, attributes);
                break;
              case 2:
                deleteArea(0, R, columns, 1, attributes);
                break;
            }
            break;
          case 'J':
            switch (DCEvars[0]) {
              case 0:
                if (R < rows - 1)
                  deleteArea(0, R + 1, columns, rows - R - 1, attributes);
                if (C < columns - 1)
                  deleteArea(C, R, columns - C, 1, attributes);
                break;
              case 1:
                if (R > 0)
                  deleteArea(0, 0, columns, R, attributes);
                if (C > 0)
                  deleteArea(0, R, C + 1, 1, attributes);// include up to and including current
                break;
              case 2:
                deleteArea(0, 0, columns, rows, attributes);
                break;
            }
            if (debug > 1)
              System.out.println("ESC [ " + DCEvars[0] + " J");
            break;
          case '@':
            if (debug > 1)
              System.out.println("ESC [ " + DCEvars[0] + " @");
            for (int i = 0; i < DCEvars[0]; i++)
              insertChar(C, R, ' ', attributes);
            break;
          case 'X':
            {
              int toerase = DCEvars[0];
              if (debug > 1)
                System.out.println("ESC [ " + DCEvars[0] + " X, C=" + C + ",R=" + R);
              if (toerase == 0)
                toerase = 1;
              if (toerase + C > columns)
                toerase = columns - C;
              deleteArea(C, R, toerase, 1, attributes);
              // does not change cursor position
              break;
            }
          case 'P':
            if (debug > 1)
              System.out.println("ESC [ " + DCEvars[0] + " P, C=" + C + ",R=" + R);
            if (DCEvars[0] == 0) DCEvars[0] = 1;
            for (int i = 0; i < DCEvars[0]; i++)
              deleteChar(C, R);
            break;
          case 'n':
            switch (DCEvars[0]) {
              case 5: 
                writeSpecial(((char) ESC) + "[0n");
                if (debug > 1)
                  System.out.println("ESC[5n");
                break;
              case 6:
                // DO NOT offset R and C by 1! (checked against /usr/X11R6/bin/resize
                // FIXME check again.
                // FIXME: but vttest thinks different???
                writeSpecial(((char) ESC) + "[" + R + ";" + C + "R");
                if (debug > 1)
                  System.out.println("ESC[6n");
                break;
              default:
                if (debug > 0)
                  System.out.println("ESC [ " + DCEvars[0] + " n??");
                break;
            }
            break;
          case 's':  
            Sc = C;
            Sr = R;
            Sa = attributes;
            if (debug > 3)
              System.out.println("ESC[s");
            break;
          case 'u': 
            C = Sc;
            R = Sr;
            attributes = Sa;
            if (debug > 3)
              System.out.println("ESC[u");
            break;
          case 'm':  
            if (debug > 3)
              System.out.print("ESC [ ");
            if (DCEvar == 0 && DCEvars[0] == 0)
              attributes = 0;
            for (int i = 0; i <= DCEvar; i++) {
              switch (DCEvars[i]) {
                case 0:
                  if (DCEvar > 0) {
                    if (terminalID.equals("scoansi")) {
                      attributes &= COLOR; 
                    } else {
                      attributes = 0;
                    }
                  }
                  break;
                case 1:
                  attributes |= BOLD;
                  attributes &= ~LOW;
                  break;
                case 2:
                  if (terminalID.equals("scoansi") && ((DCEvar - i) >= 2)) {
                    int ncolor;
                    attributes &= ~(COLOR | BOLD);

                    ncolor = DCEvars[i + 1];
                    if ((ncolor & 8) == 8)
                      attributes |= BOLD;
                    ncolor = ((ncolor & 1) << 2) | (ncolor & 2) | ((ncolor & 4) >> 2);
                    attributes |= ((ncolor) + 1) << COLOR_FG_SHIFT;
                    ncolor = DCEvars[i + 2];
                    ncolor = ((ncolor & 1) << 2) | (ncolor & 2) | ((ncolor & 4) >> 2);
                    attributes |= ((ncolor) + 1) << COLOR_BG_SHIFT;
                    i += 2;
                  } else {
                    attributes |= LOW;
                  }
                  break;
                case 4:
                  attributes |= UNDERLINE;
                  break;
                case 7:
                  attributes |= INVERT;
                  break;
                case 8:
                  attributes |= INVISIBLE;
                  break;
                case 5: 
                  break;
                case 10:
                  gl = 0;
                  usedcharsets = true;
                  break;
                case 11: 
                case 12:
                  gl = 1;
                  usedcharsets = true;
                  break;
                case 21: 
                  attributes &= ~(LOW | BOLD);
                  break;
                case 25: 
                  break;
                case 27:
                  attributes &= ~INVERT;
                  break;
                case 28:
                  attributes &= ~INVISIBLE;
                  break;
                case 24:
                  attributes &= ~UNDERLINE;
                  break;
                case 22:
                  attributes &= ~BOLD;
                  break;
                case 30:
                case 31:
                case 32:
                case 33:
                case 34:
                case 35:
                case 36:
                case 37:
                  attributes &= ~COLOR_FG;
                  attributes |= ((DCEvars[i] - 30) + 1) << COLOR_FG_SHIFT;
                  break;
                case 39:
                  attributes &= ~COLOR_FG;
                  break;
                case 40:
                case 41:
                case 42:
                case 43:
                case 44:
                case 45:
                case 46:
                case 47:
                  attributes &= ~COLOR_BG;
                  attributes |= ((DCEvars[i] - 40) + 1) << COLOR_BG_SHIFT;
                  break;
                case 49:
                  attributes &= ~COLOR_BG;
                  break;

                default:
                  System.out.println("ESC [ " + DCEvars[i] + " m unknown...");
                  break;
              }
              if (debug > 3)
                System.out.print("" + DCEvars[i] + ";");
            }
            if (debug > 3)
              System.out.print(" (attributes = " + attributes + ")m \n");
            break;
          default:
            System.out.println("ESC [ unknown letter:" + c + " (" + ((int) c) + ")");
            break;
        }
        break;
      default:
        term_state = TSTATE_DATA;
        break;
    }
    if (C > columns) C = columns;
    if (R > rows) R = rows;
    if (C < 0) C = 0;
    if (R < 0) R = 0;
    if (doshowcursor)
      setCursorPosition(C, R);
    markLine(R, 1);
  }

  public void reset() {
    gx[0] = 'B';
    gx[1] = '0';
    gx[2] = 'B';
    gx[3] = 'B';
    gl = 0;  // default GL to G0
    gr = 1;  // default GR to G1
    int nw = getColumns();
    if (nw < 132) nw = 132;
    Tabs = new byte[nw];
    for (int i = 0; i < nw; i += 8) {
      Tabs[i] = 1;
    }
    term_state = TSTATE_DATA;
  }
}
