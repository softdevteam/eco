import java.applet.*;
import java.awt.*;

public class EventTester extends Applet {
    // display the instructions
    public void paint(Graphics g)  { 
        g.drawString("Click, drag, and type in this window.", 10, 20);
    }
    
    // Handle mouse events
    @Override
    public boolean mouseDown(Event e, int x, int y)  {
        showStatus(modifier_key_names(e.modifiers) + 
               "Mouse Down: [" + x + "," + y + "]");
        return true;
    }
    public boolean mouseUp(Event e, int x, int y)  {
        showStatus(modifier_key_names(e.modifiers) + 
               "Mouse Up: [" + x + "," + y + "]");
        return true;
    }
    public boolean mouseDrag(Event e, int x, int y)  {
        showStatus(modifier_key_names(e.modifiers) + 
               "Mouse Drag: [" + x + "," + y + "]");
        return true;
    }
    public boolean mouseEnter(Event e, int x, int y)  {
        showStatus("Mouse Enter: [" + x + "," + y + "]");
        return true;
    }
    public boolean mouseExit(Event e, int x, int y)  {
        showStatus("Mouse Exit: [" + x + "," + y + "]");
        return true;
    }
    
    // Handle focus events
    public boolean gotFocus(Event e, Object what)  {
        showStatus("Got Focus");
        return true;
    }
    public boolean lostFocus(Event e, Object what)  {
        showStatus("Lost Focus");
        return true;
    }
    
    // Handle key down and key up events
    public boolean keyDown(Event e, int key)  {
        int flags = e.modifiers;
        if (e.id == Event.KEY_PRESS)            // a regular key
            showStatus("Key Down: " 
                   + modifier_key_names(flags) 
                   + key_name(e));
        else if (e.id == Event.KEY_ACTION)      // a function key
            showStatus("Function Key Down: "
                   + modifier_key_names(flags)
                   + function_key_name(key));
        return true;
    }
    public boolean keyUp(Event e, int key)  {
        int flags = e.modifiers;
        if (e.id == Event.KEY_RELEASE)             // a regular key
            showStatus("Key Up: " 
                   + modifier_key_names(flags)
                   + key_name(e));
        else if (e.id == Event.KEY_ACTION_RELEASE) // a function key
            showStatus("Function Key Up: "
                   + modifier_key_names(flags)
                   + function_key_name(key));
        return true;
    }
    
    // The remaining methods help us sort out the various key events

    // Return the current list of modifier keys
    private String modifier_key_names(int flags) {
        String s = "[ ";
        if (flags == 0) return "";
        if ((flags & Event.SHIFT_MASK) != 0) s += "Shift ";
        if ((flags & Event.CTRL_MASK) != 0) s += "Control ";
        if ((flags & Event.META_MASK) != 0) s += "Meta ";
        if ((flags & Event.ALT_MASK) != 0) s += "Alt ";
        s += "] ";
        return s;
    }
    
    // Return the name of a regular (ASCII) key.
    private String key_name(Event e) {
        char c = (char) e.key;
        
        // If CTRL flag is set, handle ASCII control characters.
        if (e.controlDown()) {
            if (c < ' ') {
                c += '@';
                return "^" + c;
            }
        }
        else {
            // If CTRL flag is not set, then certain ASCII
            // control characters have special meaning.
            switch (c) {
                case '\n': return "Return";
                case '\t': return "Tab";
                case '\033': return "Escape";
                case '\010': return "Backspace";
            }
        }

        // Handle the remaining possibilities.
        if (c == '\177') return "Delete";
        else if (c == ' ') return "Space";
        else return String.valueOf(c);
    }
    
    // Return the name of a function key.
    private String function_key_name(int key) {
        switch(key) {
            case Event.HOME: return "Home";
            case Event.END: return "End";
            case Event.PGUP: return "Page Up";
            case Event.PGDN: return "Page Down";
            case Event.UP: return "Up Arrow";
            case Event.DOWN: return "Down Arrow";
            case Event.LEFT: return "Left Arrow";
            case Event.RIGHT: return "Right Arrow";
            case Event.F1: return "F1";    case Event.F2: return "F2";
            case Event.F3: return "F3";    case Event.F4: return "F4";
            case Event.F5: return "F5";    case Event.F6: return "F6";
            case Event.F7: return "F7";    case Event.F8: return "F8";
            case Event.F9: return "F9";    case Event.F10: return "F10";
            case Event.F11: return "F11";    case Event.F12: return "F12";
        }
        return "Unknown Function Key";
    }
}
