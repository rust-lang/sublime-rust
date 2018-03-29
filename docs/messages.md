# Messages

There are a variety of ways to display Rust compiler messages. See
[Settings](../README.md#settings) for more details about how to configure
settings.

## Inline Phantoms vs Output Panel

The `show_errors_inline` setting controls whether or not errors are shown
inline with the code using Sublime's "phantoms".  If it is `true`, it will
also display an abbreviated message in the output panel.  If it is `false`,
messages will only be displayed in the output panel, using rustc's formatting.

### `show_errors_inline`

<table>
  <tr>
    <td><code>true</code></td>
    <td><img src="img/show_errors_inline_true.png"></td>
  </tr>
  <tr>
    <td><code>false</code></td>
    <td><img src="img/show_errors_inline_false.png"></td>
  </tr>
</table>

## Popup Phantom Style

Phantoms can be displayed inline with the code, or as a popup when the mouse
hovers over an error (either the gutter icon or the error outline).  The
`rust_phantom_style` setting controls this behavior.

### `rust_phantom_style`

| Value | Description |
| :---- | :---------- |
| `normal` | Phantoms are displayed inline. |
| `popup` | Phantoms are displayed when the mouse hovers over an error. |
| `none` | Phantoms are not displayed. |

<img src="img/messages_popup.gif">

## Phantom Themes

The style of the phantom messages is controlled with the `rust_message_theme`
setting.  Currently the following themes are available:

### `rust_message_theme`

<table>
  <tr>
    <td><code>clear</code></td>
    <td><img src="img/theme_clear.png"></td>
  </tr>
  <tr>
    <td><code>solid</code></td>
    <td><img src="img/theme_solid.png"></td>
  </tr>
</table>

### Clear Theme Colors

The `clear` theme is designed to integrate with your chosen Color Scheme.  You
can customize the colors of the messages with the following settings.

| Setting | Default | Description |
| :------ | :------ | :---------- |
| `rust_syntax_error_color` | `"var(--redish)"` | Color of error messages. |
| `rust_syntax_warning_color` | `"var(--yellowish)"` | Color of warning messages. |
| `rust_syntax_note_color` | `"var(--greenish)"` | Color of note messages. |
| `rust_syntax_help_color` | `"var(--bluish)"` | Color of help messages. |


## Region Highlighting

The span of code for a compiler message is by default highlighted with an
outline.

### `rust_region_style`

| Value | Example | Description |
| :---- | :------ | :---------- |
| `outline` | <img src="img/region_style_outline.png"> | Regions are highlighted with an outline. |
| `none` | <img src="img/region_style_none.png"> | Regions are not highlighted. |

## Gutter Images

The gutter (beside the line numbers) will include an icon indicating the level
of the message.  The styling of these icons is controlled with
`rust_gutter_style`.

### `rust_gutter_style`

| Value | Description |
| :---- | :---------- |
| `shape` | <img src="../images/gutter/shape-error.png"> <img src="../images/gutter/shape-warning.png"> <img src="../images/gutter/shape-note.png"> <img src="../images/gutter/shape-help.png"> |
| `circle` | <img src="../images/gutter/circle-error.png"> <img src="../images/gutter/circle-warning.png"> <img src="../images/gutter/circle-note.png"> <img src="../images/gutter/circle-help.png"> |
| `none` | Do not display icons. |

## Other Settings

A few other settings are available for controlling messages:

| Setting | Default | Description |
| :------ | :------ | :---------- |
| `show_panel_on_build` | `true` | If true, an output panel is displayed at the bottom of the window showing the compiler output. |
| `rust_syntax_hide_warnings` | `false` | If true, will not display warning messages. |
