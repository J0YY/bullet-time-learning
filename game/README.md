# Instrumented projectile arena

An original minimal scripted Godot launch-and-hit game. A projectile is launched
at a rigid target stack; impacts, displacement and shot outcomes are recorded only
in private state/evidence exports. The rendered RGB has no UI, score or state text.
This integration scene does not yet establish benchmark diversity or visual task
solvability. All meshes and materials are generated from source; no external assets.

`arena_driver.gd simulate` runs fixed 64 Hz Godot physics and saves 16 states.
`arena_driver.gd render` starts a separate process containing only replay meshes,
fixed lighting and a camera. It saves each RGB cell once for model use; mask passes
and four repeat captures per grid are validation artifacts outside the RGB root.
The repeat captures never replace or augment a condition's training images.

The pinned macOS compatibility renderer requires a native display. Godot's headless
display is used for simulation only; a successful headless process cannot certify
RGB output. Pin/validate another platform before claiming it reproduces these bytes.

See [producer commands](../docs/arena-producer.md) for the staged build/validation.
Original arena code/material descriptions are MIT-licensed in [LICENSE](LICENSE).
Godot has its own [MIT license](https://github.com/godotengine/godot/blob/4.5.1-stable/LICENSE.txt).
References: [saved-state replay design](../SPEC.md),
[Godot viewport capture](https://docs.godotengine.org/en/4.5/tutorials/rendering/viewports.html),
[rigid-body control](https://docs.godotengine.org/en/4.5/classes/class_rigidbody3d.html).
