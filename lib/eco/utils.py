# Copyright (c) 2013--2016 King's College London
# Created by the Software Development Team <http://soft-dev.org/>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.

import sys

from PyQt4.QtCore import Qt

arrow_keys = {
    Qt.Key_Up: "up",
    Qt.Key_Down: "down",
    Qt.Key_Left: "left",
    Qt.Key_Right: "right"
}

reversed_arrow_keys = {
    "up": Qt.Key_Up,
    "down": Qt.Key_Down,
    "left": Qt.Key_Left,
    "right": Qt.Key_Right
}

modifier_keys = set([Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Control, Qt.Key_Meta, Qt.Key_AltGr])

class BaseKeyPress(object):
    def __init__(self, event):
        self._event = event
        self.key = event.key()
        self.modifiers = event.modifiers()
        self.native_modifiers = event.nativeModifiers()

    @property
    def is_arrow(self):
        return self.key in arrow_keys

    @property
    def is_modifier(self):
        return self.key in modifier_keys

    @property
    def m_shift(self):
        return self.modifiers == Qt.ShiftModifier

    @property
    def m_control(self):
        return self.modifiers == Qt.ControlModifier

    @property
    def m_alt(self):
        return self.modifiers == Qt.AltModifier

    @property
    def has_action_modifier(self):
        return self.m_control or self.m_alt

    @property
    def escape(self):
        return self.key == Qt.Key_Escape

    @property
    def backspace(self):
        return self.key == Qt.Key_Backspace

    @property
    def delete(self):
        return self.key == Qt.Key_Delete

    @property
    def home(self):
        return self.key == Qt.Key_Home

    @property
    def end(self):
        return self.key == Qt.Key_End

    @property
    def left(self):
        return self.key == Qt.Key_Left

    @property
    def right(self):
        return self.key == Qt.Key_Right

    @property
    def up(self):
        return self.key == Qt.Key_Up

    @property
    def down(self):
        return self.key == Qt.Key_Down

    @property
    def page_up(self):
        return self.key == Qt.Key_PageUp

    @property
    def page_down(self):
        return self.key == Qt.Key_PageDown

    jump_word = m_control


class OSXKeyPress(BaseKeyPress):
    COMMAND = 0x100 #
    SHIFT = 0x200
    CAPSLOCK = 0x400
    ALT = 0x800
    META = 0x1000 # labeled `control` on mac keyboards

    @property
    def m_shift(self):
        return bool(self.native_modifiers & self.SHIFT)

    @property
    def m_control(self):
        return bool(self.native_modifiers & self.COMMAND)

    @property
    def m_alt(self):
        return bool(self.native_modifiers & self.ALT)

    @property
    def home(self):
        return (
            BaseKeyPress.home.fget(self)
            or self.m_control and self.left
            or self.m_alt and self.up
        )

    @property
    def end(self):
        return (
            BaseKeyPress.end.fget(self)
            or self.m_control and self.right
            or self.m_alt and self.down
        )

    jump_word = m_alt


if sys.platform == "darwin":
    KeyPress = OSXKeyPress
else:
    KeyPress = BaseKeyPress


class MockedKeyPress(KeyPress):
    def __init__(self, key, modifiers=None):
        self.key = key
        self.modifiers = modifiers if modifiers is not None else set()

    @property
    def m_shift(self):
        return "shift" in self.modifiers

    @property
    def m_control(self):
        return "control" in self.modifiers

    @property
    def m_alt(self):
        return "alt" in self.modifiers

KEY_LEFT = MockedKeyPress(reversed_arrow_keys["left"])
KEY_RIGHT = MockedKeyPress(reversed_arrow_keys["right"])
KEY_UP = MockedKeyPress(reversed_arrow_keys["up"])
KEY_DOWN = MockedKeyPress(reversed_arrow_keys["down"])
