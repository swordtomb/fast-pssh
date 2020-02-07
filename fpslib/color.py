
def r(string): return with_color(string, 31) # Red
def g(string): return with_color(string, 32) # Green
def y(string): return with_color(string, 33) # Yellow
def b(string): return with_color(string, 34) # Blue
def m(string): return with_color(string, 35) # Magenta
def c(string): return with_color(string, 36) # Cyan
def w(string): return with_color(string, 37) # White

# Python cookbook #475186
def has_colors(stream):
    if not hasattr(stream, "isatty") or not stream.isatty():
        return False
    try:
        import curses
        curses.setupterm()
        return curses.tigetnum("colors") > 2
    except:
        return False
