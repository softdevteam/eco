import java.applet.*;
import java.awt.*;

public class SecondApplet extends Applet {
    static final String message = "Hello World";
    private Font font;

    // One-time initialization for the applet
    public void init() {
        font = new Font("Helvetica", Font.BOLD, 48);
    }

    // Draw the applet whenever necessary.  Do some fancy graphics.
    public void paint(Graphics g) {
        // The pink oval
        g.setColor(Color.pink);
        g.fillOval(10, 10, 330, 100);
        
        // The red outline.  java doesn't support wide lines, so we
        // try to simulate a 4-pixel wide line by drawing four ovals
        g.setColor(Color.red);
        g.drawOval(10,10, 330, 100);
        g.drawOval(9, 9, 332, 102);
        g.drawOval(8, 8, 334, 104);
        g.drawOval(7, 7, 336, 106);

        // The text
        g.setColor(Color.black);
        g.setFont(font);
        g.drawString(message, 40, 75);
    }
}