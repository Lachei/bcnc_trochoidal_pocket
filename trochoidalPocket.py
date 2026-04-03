"""
Trochoidal Pocket Plugin for bCNC

Creates a rectangular pocket using a trochoidal (circular looping) toolpath.

Author: Stumpfegger Josef josefstumpfegger@outlook.de
"""

from __future__ import absolute_import
from CNC import CNC, Block
from ToolsPage import Plugin

import math


class Tool(Plugin):
    __doc__ = "Trochoidal rectangular pocket"

    def __init__(self, master):
        Plugin.__init__(self, master, "TrochoidalPocket")

        self.icon = "trochoidal"
        self.group = "CAM"

        self.variables = [
            ("width", "mm", 50.0, "Pocket width"),
            ("height", "mm", 30.0, "Pocket height"),
            ("depth", "mm", -5.0, "Total depth (negative)"),
            ("stepdown", "mm", 1.0, "Depth per pass"),
            ("dive_slope", "mm", 1.0, "Dive in spiral slope"),
            ("tool_diam", "mm", 6.0, "Tool diameter"),
            ("stepover", "mm", 2.0, "Trochoidal step over"),
            ("radius", "mm", 3.0, "Trochoidal loop radius"),
            ("feed", "mm/s", 20, "Feed rate in mm/s"),
            ("rpm", "int", 10000, "Spindle RPM"),
        ]

        self.buttons.append("exe")

    def execute(self, app):
        width = self["width"]
        height = self["height"]
        depth = self["depth"]
        stepdown = self["stepdown"]
        dive_slope = self["dive_slope"]
        tool_diam = self["tool_diam"]
        stepover = self["stepover"]
        radius = self["radius"]
        feed = int(self["feed"]) * 60 # convert to mm per minutes
        rpm = self["rpm"]

        outer_w = width
        outer_h = height
        width -= tool_diam + radius
        height -= tool_diam + radius
        print(f"width {width}, height {height}, tool_diam {tool_diam}, radius {radius}")
        if width <= 0:
            print("Error: too small width for path")
            return
        if height <= 0:
            print("Error: too small height for path")
            return

        block = Block("Trochoidal Pocket")

        # Start position
        x0, y0 = radius , radius 
        safe_z = 5

        # Spindle on
        block.append(f"M3 S{rpm}")
        block.append("G21") # set metric mode

        prev_depth = 0
        current_depth = 0

        # Trochoidal loop (circle segments)
        segments = 24

        while current_depth > depth:
            current_depth -= stepdown
            if current_depth < depth:
                current_depth = depth

            block.append(f"G0 Z{safe_z}")
            block.append(f"G0 X{x0:.3f} Y{y0:.3f}")
            descent_d = prev_depth
            while descent_d > current_depth:
                for i in range(segments):
                    descent_d -= dive_slope / segments
                    if descent_d < current_depth:
                        descent_d = current_depth
                    angle = 1.5 * math.pi + 2 * math.pi * i / segments
                    cx = x0 + radius * math.cos(angle)
                    cy = y0 + radius * math.sin(angle)
                    block.append(f"G1 X{cx:.3f} Y{cy:.3f} Z{descent_d:.3f} F{feed}")

            y = y0
            direction = 1

            y_done = False
            while True:
                x = x0 if direction == 1 else width

                while True :

                    for i in range(segments - 1):
                        angle = 1.5 * math.pi - 2 * math.pi * i / segments
                        cx = x + radius * math.cos(angle)
                        cy = y + radius * math.sin(angle)
                        block.append(f"G1 X{cx:.3f} Y{cy:.3f} F{feed}")

                    if (direction == 1 and x == width) or (direction == -1 and x == x0):
                        break
                    x += stepover * direction
                    if direction == 1 and x > width:
                        x = width
                    if direction == -1 and x < x0:
                        x = x0

                if y == height:
                    break
                cur_y = y
                y += 2 * radius + tool_diam - 2
                if (y > height):
                    y = height
                while True: 
                    for i in range(segments + 1):
                        angle = -2 * math.pi * i / segments
                        cx = x + radius * math.cos(angle)
                        cy = cur_y + radius * math.sin(angle)
                        block.append(f"G1 X{cx:.3f} Y{cy:.3f} F{feed}")
                    if cur_y == y:
                        break
                    cur_y += stepover
                    if cur_y > y:
                        cur_y = y
                direction *= -1
                prev_depth = current_depth

        # final pocket
        current_depth = 0
        while current_depth > depth:
            current_depth -= stepdown
            if current_depth < depth:
                current_depth = depth

            block.append(f"G0 Z{safe_z:.3f}")
            block.append(f"G0 X{x0:.3f} Y{y0:.3f}")
            block.append(f"G0 Z{current_depth:.3f}")
            block.append(f"G1 X{0} Y{0} Z{current_depth:.3f} F{feed}")
            block.append(f"G1 X{outer_w - tool_diam} Y{0} F{feed}")
            block.append(f"G1 X{outer_w - tool_diam} Y{outer_h - tool_diam} F{feed}")
            block.append(f"G1 X{0} Y{outer_h - tool_diam} F{feed}")
            block.append(f"G1 X{0} Y{0} F{feed}")

        # Retract
        block.append(f"G0 Z{safe_z}")
        block.append("M5")

        # Insert into bCNC
        app.gcode.insBlocks(app.activeBlock(), [block], "Trochoidal Pocket")
        app.refresh()
