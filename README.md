# matchstack
A stupid python arson wrapper to debug dta node numbers

![pic2](/media/pic2.png)

# About
This script is meant to be used in conjunction with [arsonc](https://github.com/hmxmilohax/arson) to provide a easy to read node id identification for given node numbers, to help with debugging debug enabled Harmonix games.

When a Harmonix debug build crashes, a `stack` trace is given, including line numbers meant to `match` up with node numbers in dtb.

Previously, the only available tool to check these correct node numbers was [GH2 dtb editor](https://www.scorehero.com/forum/viewtopic.php?p=160594), a heavily antiquated tool by today's standards.

`matchstack` aims to make finding these node numbers a more pleasant experience with `arsonc`

`arsonc` has its own new decompile flag that will print node id's in the output dta, `matchstack` simply makes this a bit more legible and simple.

`matchstack` automatically copies the input dta to a tmp folder, use `arsonc` to compile to dtb, then decompiled the dtb back to dta, with node id information.

The processed output of the dta is printed to console with syntax highlighting and contextual script around the searched id.

# Usage
* Compile or download the latest action build of [arson](https://github.com/hmxmilohax/arson)
* arson version must be greater than `16641e83b65ac1e00b836acfa13eb6e0ea505575`
* if on Windows, place `arsonc.exe`  `matchstack.py`
* usage: matchstack.py [-h] input_file target_id

* Note, arsonc labels node's one off from the correct node id
* The script accounts for this in seek, but does not change ID's arsonc generates, so the node labels may seem off by 1 until this is fixed.

# Disclaimer
* Disclaimer, this script was written by AI, this readme was not.