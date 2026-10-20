# Ripple: An Overlap Tool for Maya

Ripple is a Maya window that takes the animation on one "driver" object and passes it to the other selected objects, each one a little later and a little weaker, so their motion ripples through the group in one click.

- **App:** Autodesk Maya (tested in Maya ____ ← fill in your version)
- **Language:** Python, PySide2/PySide6 (built into Maya, nothing to install)

---

## Install and run

You need Maya. No other installs.

**1. Get the files.** Clone this repo, or click **Code → Download ZIP** on GitHub and unzip it. Note the folder path, for example `C:/Users/you/Documents/pfa-midterm`.

The folder contains:
- `ripple.py`: the tool
- `make_test_scene.py`: builds a demo scene to try it on

**2. Open Maya's Script Editor.** Go to **Windows → General Editors → Script Editor**, then click the **Python** tab (not MEL).

**3. Build the test scene.** This replaces the current scene, so save any work first. Paste the code below, change the path to your folder (keep the `r` and use forward slashes), then press **Ctrl+Enter**:

```python
import sys, importlib
sys.path.append(r"C:/Users/you/Documents/pfa-midterm")
import make_test_scene; importlib.reload(make_test_scene); make_test_scene.build()
```

You should see a sphere in the middle and 16 shapes in two rings around it, all selected.

**4. Open Ripple.** Paste and run:

```python
import ripple; importlib.reload(ripple); ripple.show()
```

**5. Use it.**
1. With everything still selected, click **Load Selection**. The sphere becomes the driver, and the 16 shapes are listed as followers.
2. Drag the **Delay** and **Falloff** sliders and watch the graph change.
3. Check **Scale** if you also want the squash and stretch.
4. Click **Apply**, then press play in the timeline. The shapes copy the sphere's bounce and spin one after another, each a bit smaller.
5. Press **Ctrl+Z** once. The whole ripple is undone.

**Using it on your own scene:** animate one object, select it **first**, then shift-select the objects that should follow, in the order you want them to move. Then do step 5.

---

## What works now

- The Ripple window opens inside Maya with every control laid out.
- **Load Selection:** first selected object = driver, the rest = followers.
- **Delay** and **Falloff** sliders.
- **Translate, Rotate, and Scale** channels can be rippled.
- **Apply** in selection order. Each object keeps its own position, rotation, and scale, and moves relative to where it already was.
- **One Ctrl+Z** undoes the whole Apply.
- **Live graph:** shows a sample wave, then the driver's real curve after Load Selection, and redraws while you drag the sliders.
- **Error messages** instead of crashes: fewer than 2 objects, no keys on the driver, no channels checked, locked channels, objects deleted after loading.

## Not working yet (planned for Oct 26)

- **Order menu** (distance from driver, left to right). It's visible but Apply always uses selection order.
- **Preview / Revert** buttons (they show a "planned" message).
- **Presets:** the menu is visible but doesn't change settings yet, and **Save** doesn't work yet.
- **Remembering settings** between Maya sessions.
- Followers get the driver's key times and values, but not its tangent types yet.

---

## Peer run

**Classmate:** ____

> ____ (their three sentences: what they did, what happened, what confused them or broke)

**What I'll fix next week:** ____

---

## Original pitch

### The chore it ends
In my animation class I often need many things to move one after another: a tail or hair chain swinging (overlapping action), or a group of objects popping, bouncing, or spinning in a wave. Today I key one object, copy its keys to every other object by hand, shift each one a few frames later in the Graph Editor, and adjust the values so each object keeps its own position and the motion fades. For 5–10 objects this takes about 20–40 minutes, and I redo it every time I change the main motion.

### Why it's advanced
Works on any selection, keeps each object in its own place, smart ordering, a live graph, preview before committing, presets, remembered settings, error handling, and one-step undo.

### The three weeks
- **Oct 13:** window opens with every control, Load Selection fills the lists.
- **Oct 20:** Apply works with delay, falloff, one-step undo, and error messages; the graph redraws with the sliders.
- **Oct 26:** Order menu, Preview/Revert, presets, saved settings; tested on a tail rig and a mixed-shape scene.

### Smallest version that still counts
Load Selection, Delay and Falloff, and Apply rippling Translate and Rotate in selection order as one undoable step.

### Riskiest part
Keeping every object in its own place (adding the driver's change rather than copying its values, with scale fading toward 1), restoring keys reliably for Revert, and drawing the custom graph.
