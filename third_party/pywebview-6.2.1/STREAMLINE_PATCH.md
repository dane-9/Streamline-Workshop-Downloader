# Streamline pywebview fork

This directory vendors pywebview 6.2.1 under its BSD 3-Clause license.
Streamline identifies the patched package as `6.2.1+streamline.1`.

## Wayland changes

- Qt drag regions call `QWindow.startSystemMove()` instead of repeatedly
  positioning the top-level window with `QWidget.move()`.
- The `Window.start_system_resize(edge)` extension dispatches
  `QWindow.startSystemResize()` on Qt's GUI thread.
- Other pywebview renderers retain their existing coordinate-based drag path.

These changes are needed because the Wayland XDG shell does not permit clients
to position top-level windows. Interactive moves and resizes must be initiated
through the compositor.
