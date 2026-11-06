# Motion attribution

The centered login/registration card uses Vanilla Tilt 1.8.1 by Sergiu Șandor,
MIT licensed: https://github.com/micku7zu/vanilla-tilt.js.
Its license is included in public/licenses/VanillaTilt-MIT.txt and distributed with the build.

The ribbon() formula and ribbon field arrangement in src/components/motion/ribbon.ts
are adapted from ThreeUI Community by Meng To, MIT licensed.
Source: https://github.com/MengTo/threeui/blob/main/src/shaders/ribbon-field/ribbonFieldShaders.ts
License included in public/licenses/ThreeUI-MIT.txt and distributed with the build.

This adaptation uses theme colour uniforms, no original neon palette, grid, bloom,
third-party media or fonts. Native WebGL rendering is lazy loaded only on desktop
with motion enabled. It runs continuously while visible with a pause/play control,
pauses offscreen/when hidden, limits DPR to 1.25 and rendering to 30fps, and disposes
all observers, events and GPU objects on unmount. Unsupported WebGL and mobile use CSS purple waves. Reduced motion uses a static surface. No React or Three.js dependency is required.

Route, hover, button and loading interactions are original Vue/CSS implementations
informed by the ThreeUI interaction examples. No Pro or Beta components are used.
Loading feedback reflects actual existing work; no simulated progress is introduced.
